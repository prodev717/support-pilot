import os
import tempfile
from pathlib import Path
from uuid import uuid4
from datetime import datetime, UTC
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pinecone import Pinecone
from sqlalchemy import Column, Integer, String, DateTime, func, create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
DATABASE_URL = os.getenv("DATABASE_URL")
PINECONE_NAMESPACE = "support-pilot"

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY missing")
if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME missing")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------

# psycopg3 dialect: postgresql+psycopg://
_db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(_db_url, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    chunk_id = Column(Integer, nullable=False)
    pinecone_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# FastAPI lifespan — create tables if they don't exist
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------------------------
# Pinecone
# ---------------------------------------------------------------------------

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# ---------------------------------------------------------------------------
# Document extraction via LangChain loaders
# ---------------------------------------------------------------------------

def extract_text(content: bytes, extension: str) -> str:
    """Write bytes to a temp file, load with the appropriate LangChain loader."""
    suffix = extension  # e.g. ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        if extension == ".pdf":
            loader = PyPDFLoader(tmp_path)
        elif extension == ".docx":
            loader = Docx2txtLoader(tmp_path)
        else:  # .txt
            loader = TextLoader(tmp_path, encoding="utf-8")
        docs = loader.load()
        return "\n\n".join(doc.page_content for doc in docs)
    finally:
        os.unlink(tmp_path)

# ---------------------------------------------------------------------------
# Chunking via LangChain RecursiveCharacterTextSplitter
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)

# ---------------------------------------------------------------------------
# Metadata helpers (ORM)
# ---------------------------------------------------------------------------

def save_metadata(rows: list[dict]):
    with Session(engine) as session:
        session.add_all([
            DocumentMetadata(
                document_id=row["document_id"],
                filename=row["filename"],
                chunk_id=row["chunk_id"],
                pinecone_id=row["pinecone_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ])
        session.commit()


def store_chunks(filename: str, chunks: list[str]) -> str:
    document_id = str(uuid4())
    upload_time = datetime.now(UTC)
    records = []
    metadata_rows = []
    for i, chunk in enumerate(chunks):
        vector_id = f"{document_id}_chunk_{i}"
        records.append({
            "_id": vector_id,
            "text": chunk,
            "document_id": document_id,
            "filename": filename,
            "chunk_id": i,
            "upload_time": upload_time,
        })
        metadata_rows.append({
            "document_id": document_id,
            "filename": filename,
            "chunk_id": i,
            "pinecone_id": vector_id,
            "created_at": upload_time,  # datetime object
        })
    index.upsert_records(namespace=PINECONE_NAMESPACE, records=records)
    save_metadata(metadata_rows)
    return document_id


def search_chunks(query: str, top_k: int = 5):
    return index.search(
        namespace=PINECONE_NAMESPACE,
        top_k=top_k,
        inputs={"text": query},
    )


def delete_document(document_id: str) -> int:
    with Session(engine) as session:
        rows = (
            session.query(DocumentMetadata)
            .filter(DocumentMetadata.document_id == document_id)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Document not found")
        ids = [row.pinecone_id for row in rows]
        index.delete(ids=ids, namespace=PINECONE_NAMESPACE)
        for row in rows:
            session.delete(row)
        session.commit()
        return len(ids)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html")


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    overlap: int = Form(200),
):
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only pdf, docx, txt files allowed")

    content = await file.read()

    try:
        text = extract_text(content, extension)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text found in document")

    try:
        chunk_size = int(chunk_size)
        overlap = int(overlap)
    except Exception:
        raise HTTPException(status_code=400, detail="chunk_size and overlap must be integers")

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="Invalid chunk_size/overlap values")

    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=overlap)
    document_id = store_chunks(file.filename, chunks)
    return {
        "status": "success",
        "document_id": document_id,
        "filename": file.filename,
        "chunks": len(chunks),
    }


@app.get("/search")
async def search(query: str, top_k: int = 5):
    try:
        top_k = int(top_k)
    except Exception:
        raise HTTPException(status_code=400, detail="top_k must be an integer")
    results = search_chunks(query=query, top_k=top_k)
    matches = [
        {
            "score": hit.score,
            "document_id": hit.fields.get("document_id"),
            "filename": hit.fields.get("filename"),
            "chunk_id": int(hit.fields.get("chunk_id", 0)),
            "text": hit.fields.get("text"),
        }
        for hit in results.result.hits
    ]
    return {"query": query, "results": matches}


@app.delete("/documents/{document_id}")
async def remove_document(document_id: str):
    deleted_count = delete_document(document_id)
    return {
        "status": "success",
        "document_id": document_id,
        "chunks_deleted": deleted_count,
    }


@app.get("/documents")
async def list_documents():
    with Session(engine) as session:
        rows = (
            session.query(
                DocumentMetadata.document_id,
                DocumentMetadata.filename,
                func.count().label("chunks"),
            )
            .group_by(DocumentMetadata.document_id, DocumentMetadata.filename)
            .order_by(DocumentMetadata.filename)
            .all()
        )
        return [
            {"document_id": r.document_id, "filename": r.filename, "chunks": r.chunks}
            for r in rows
        ]