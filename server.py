import os
from pathlib import Path
from io import BytesIO
from uuid import uuid4
from datetime import datetime, UTC
from contextlib import asynccontextmanager
import psycopg
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Request
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader
from docx import Document
from pinecone import Pinecone

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
DATABASE_URL = os.getenv("DATABASE_URL")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY missing")

if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME missing")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt"
}

def init_db():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(255) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    chunk_id INT NOT NULL,
                    pinecone_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_document_metadata_document_id 
                ON document_metadata(document_id);
            """)
            conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def extract_pdf_text(content: bytes) -> str:
    pdf = PdfReader(BytesIO(content))
    text = ""
    for page in pdf.pages:
        text += page.extract_text() or ""
    return text

def extract_docx_text(content: bytes) -> str:
    doc = Document(BytesIO(content))
    return "\n".join(
        paragraph.text
        for paragraph in doc.paragraphs
    )

def save_metadata(rows: list[dict]):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO document_metadata (document_id, filename, chunk_id, pinecone_id, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, [
                (
                    row["document_id"],
                    row["filename"],
                    row["chunk_id"],
                    row["pinecone_id"],
                    row["created_at"]
                ) for row in rows
            ])
            conn.commit()

def store_chunks(filename: str, chunks: list[str]):
    document_id = str(uuid4())
    upload_time = datetime.now(UTC).isoformat()
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
            "upload_time": upload_time
        })
        metadata_rows.append({
            "document_id": document_id,
            "filename": filename,
            "chunk_id": i,
            "pinecone_id": vector_id,
            "created_at": upload_time
        })
    index.upsert_records(
        namespace="support-pilot",
        records=records
    )
    save_metadata(metadata_rows)
    return document_id

def search_chunks(query: str, top_k: int = 5):
    result = index.search(
        namespace="support-pilot",
        top_k=top_k,
        inputs={"text": query}
    )
    return result

def delete_document(document_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pinecone_id 
                FROM document_metadata 
                WHERE document_id = %s
            """, (document_id,))
            rows = cur.fetchall()
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail="Document not found"
                )
            ids = [row[0] for row in rows]
            index.delete(ids=ids, namespace="support-pilot")
            cur.execute("""
                DELETE FROM document_metadata 
                WHERE document_id = %s
            """, (document_id,))
            conn.commit()
            return len(ids)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request,name="upload.html")

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    overlap: int = Form(200),
):
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only pdf, docx, txt files allowed"
        )
    content = await file.read()
    try:
        if extension == ".pdf":
            text = extract_pdf_text(content)
        elif extension == ".docx":
            text = extract_docx_text(content)
        else:
            text = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No text found in document"
        )
    # basic validation and ensure ints
    try:
        chunk_size = int(chunk_size)
        overlap = int(overlap)
    except Exception:
        raise HTTPException(status_code=400, detail="chunk_size and overlap must be integers")

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="Invalid chunk_size/overlap values")

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    document_id = store_chunks(file.filename, chunks)
    return {
        "status": "success",
        "document_id": document_id,
        "filename": file.filename,
        "chunks": len(chunks)
    }

@app.get("/search")
async def search(query: str, top_k: int = 5):
    try:
        top_k = int(top_k)
    except Exception:
        raise HTTPException(status_code=400, detail="top_k must be an integer")
    results = search_chunks(query=query, top_k=top_k)
    matches = []
    for hit in results.result.hits:
        matches.append({
            "score": hit.score,
            "document_id": hit.fields.get("document_id"),
            "filename": hit.fields.get("filename"),
            "chunk_id": int(hit.fields.get("chunk_id", 0)),
            "text": hit.fields.get("text")
        })
    return {
        "query": query,
        "results": matches
    }

@app.delete("/documents/{document_id}")
async def remove_document(document_id: str):
    deleted_count = delete_document(
        document_id
    )
    return {
        "status": "success",
        "document_id": document_id,
        "chunks_deleted": deleted_count
    }

@app.get("/documents")
async def list_documents():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT document_id, filename, COUNT(*) as chunks 
                FROM document_metadata 
                GROUP BY document_id, filename
                ORDER BY filename
            """)
            rows = cur.fetchall()
            return [
                {
                    "document_id": row[0],
                    "filename": row[1],
                    "chunks": row[2]
                }
                for row in rows
            ]