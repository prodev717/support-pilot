import os
from pathlib import Path
from io import BytesIO
from uuid import uuid4
from datetime import datetime, UTC
import pandas as pd
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
from sentence_transformers import SentenceTransformer

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY missing")

if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME missing")

CSV_FILE = "metadata.csv"

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt"
}

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


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
    df = pd.DataFrame(rows)
    if Path(CSV_FILE).exists():
        df.to_csv(CSV_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(CSV_FILE, index=False)

def store_chunks(filename: str, chunks: list[str]):
    document_id = str(uuid4())
    upload_time = datetime.now(UTC).isoformat()
    embeddings = embedding_model.encode(chunks).tolist()
    vectors = []
    metadata_rows = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vector_id = f"{document_id}_chunk_{i}"
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "document_id": document_id,
                "filename": filename,
                "chunk_id": i,
                "upload_time": upload_time,
                "text": chunk
            }
        })
        metadata_rows.append({
            "document_id": document_id,
            "filename": filename,
            "chunk_id": i,
            "pinecone_id": vector_id,
            "created_at": upload_time
        })
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i+batch_size])
    save_metadata(metadata_rows)
    return document_id

def search_chunks(query: str, top_k: int = 5):
    query_embedding = embedding_model.encode(query).tolist()
    result = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
    return result

def delete_document(document_id: str):
    if not Path(CSV_FILE).exists():
        raise HTTPException(
            status_code=404,
            detail="Metadata file not found"
        )
    df = pd.read_csv(CSV_FILE)
    rows = df[df["document_id"]== document_id]
    if rows.empty:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    ids = rows["pinecone_id"].tolist()
    index.delete(ids=ids)
    df = df[df["document_id"]!= document_id]
    df.to_csv(CSV_FILE, index=False)
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
    results = search_chunks(query=query, top_k=top_k)
    matches = []
    for match in results["matches"]:
        matches.append({
            "score": match["score"],
            "document_id":
                match["metadata"]["document_id"],
            "filename":
                match["metadata"]["filename"],
            "chunk_id":
                match["metadata"]["chunk_id"],
            "text":
                match["metadata"]["text"]
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
    if not Path(CSV_FILE).exists():
        return []
    df = pd.read_csv(CSV_FILE)
    docs = df.groupby(["document_id", "filename"]).size().reset_index(name="chunks")
    return docs.to_dict(orient="records")