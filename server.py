from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, Base, Email, DocumentMetadata, Ticket
from schemas import EmailCreate, EmailUpdate, TicketCreate, TicketUpdate, TicketSendDraft
from services import (
    extract_text,
    chunk_text,
    store_chunks,
    search_chunks,
    delete_document,
    check_database_health,
    check_pinecone_health,
)
from email_service import (
    reply_in_thread,
    send_email,
    check_email_imap_health,
    check_email_smtp_health,
)
from ai_service import check_health as check_gemini_health

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

origins = [
    "http://localhost:5173",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)


# ---------------------------------------------------------------------------
# HTML Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html")


# ---------------------------------------------------------------------------
# Document / Knowledge Base
# ---------------------------------------------------------------------------

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
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
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


# ---------------------------------------------------------------------------
# Department Email Routing
# ---------------------------------------------------------------------------

@app.get("/emails")
async def list_emails():
    with Session(engine) as session:
        rows = session.query(Email).order_by(Email.department).all()
        return [
            {
                "id": r.id,
                "department": r.department,
                "email": r.email,
                "description": r.description,
            }
            for r in rows
        ]


@app.post("/emails")
async def create_email(data: EmailCreate):
    with Session(engine) as session:
        new_email = Email(
            department=data.department,
            email=data.email,
            description=data.description,
        )
        session.add(new_email)
        session.commit()
        session.refresh(new_email)
        return {
            "status": "success",
            "email": {
                "id": new_email.id,
                "department": new_email.department,
                "email": new_email.email,
                "description": new_email.description,
            },
        }


@app.put("/emails/{email_id}")
async def update_email(email_id: int, data: EmailUpdate):
    with Session(engine) as session:
        row = session.query(Email).filter(Email.id == email_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Email not found")
        if data.department is not None:
            row.department = data.department
        if data.email is not None:
            row.email = data.email
        if data.description is not None:
            row.description = data.description
        session.commit()
        return {
            "status": "success",
            "email": {
                "id": row.id,
                "department": row.department,
                "email": row.email,
                "description": row.description,
            },
        }


@app.delete("/emails/{email_id}")
async def delete_email(email_id: int):
    with Session(engine) as session:
        row = session.query(Email).filter(Email.id == email_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Email not found")
        session.delete(row)
        session.commit()
        return {"status": "success", "id": email_id}


# ---------------------------------------------------------------------------
# Helper: serialise a Ticket row
# ---------------------------------------------------------------------------

def _ticket_row(r: Ticket) -> dict:
    return {
        "id": r.id,
        "ticket_id": r.ticket_id,
        "customer_email": r.customer_email,
        "subject": r.subject,
        "body": r.body,
        "message_id": r.message_id,
        "thread_id": r.thread_id,
        "issue": r.issue,
        "severity": r.severity,
        "sentiment": r.sentiment,
        "emotion": r.emotion,
        "ticket_status": r.ticket_status,
        "ai_decision": r.ai_decision,
        "ai_draft_reply": r.ai_draft_reply,
        "draft_sent": getattr(r, 'draft_sent', False),
        "forwarded_to": r.forwarded_to,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Tickets — list (one entry per logical ticket_id, latest message metadata)
# ---------------------------------------------------------------------------

@app.get("/tickets")
async def list_tickets(status: str | None = None):
    """
    Returns one record per logical ticket_id.
    The record reflects the most-recent message row's metadata.
    """
    with Session(engine) as session:
        # Sub-query: latest `id` per ticket_id
        sub = (
            session.query(
                Ticket.ticket_id,
                func.max(Ticket.id).label("latest_id"),
            )
            .group_by(Ticket.ticket_id)
            .subquery()
        )

        q = (
            session.query(Ticket)
            .join(sub, Ticket.id == sub.c.latest_id)
            .order_by(Ticket.created_at.desc())
        )

        if status:
            q = q.filter(Ticket.ticket_status == status)

        rows = q.all()

        # Attach message count
        counts = (
            session.query(Ticket.ticket_id, func.count(Ticket.id).label("msg_count"))
            .group_by(Ticket.ticket_id)
            .all()
        )
        count_map = {c.ticket_id: c.msg_count for c in counts}

        result = []
        for r in rows:
            d = _ticket_row(r)
            d["message_count"] = count_map.get(r.ticket_id, 1)
            result.append(d)
        return result


# ---------------------------------------------------------------------------
# Tickets — detail (full thread / all messages for a ticket_id)
# ---------------------------------------------------------------------------

@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    """
    Returns ticket metadata (latest row) plus all conversation messages.
    """
    with Session(engine) as session:
        rows = (
            session.query(Ticket)
            .filter(Ticket.ticket_id == ticket_id)
            .order_by(Ticket.created_at.asc())
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Ticket not found")

        latest = rows[-1]
        
        messages = []
        for r in rows:
            msg = _ticket_row(r)
            msg["sender"] = "user"
            messages.append(msg)
            
            if getattr(r, 'draft_sent', False) and getattr(r, 'ai_draft_reply', None):
                ai_msg = {
                    "id": f"ai_{r.id}",
                    "ticket_id": r.ticket_id,
                    "customer_email": "Support Pilot (AI)",
                    "subject": f"Re: {r.subject}" if r.subject and not r.subject.startswith("Re:") else (r.subject or ""),
                    "body": r.ai_draft_reply,
                    "created_at": r.updated_at.isoformat() if r.updated_at else (r.created_at.isoformat() if r.created_at else None),
                    "sender": "ai",
                    "issue": r.issue,
                    "severity": r.severity,
                    "sentiment": "N/A",
                    "emotion": "N/A"
                }
                messages.append(ai_msg)

        return {
            **_ticket_row(latest),
            "messages": messages,
            "message_count": len(messages),
        }


# ---------------------------------------------------------------------------
# Tickets — create
# ---------------------------------------------------------------------------

@app.post("/tickets")
async def create_ticket(data: TicketCreate):
    with Session(engine) as session:
        # Determine ticket_id
        if data.ticket_id is not None:
            ticket_id = data.ticket_id
        else:
            result = session.query(func.max(Ticket.ticket_id)).scalar()
            ticket_id = (result or 0) + 1

        new_ticket = Ticket(
            ticket_id=ticket_id,
            customer_email=data.customer_email,
            subject=data.subject,
            body=data.body,
            message_id=data.message_id,
            thread_id=data.thread_id,
            issue=data.issue,
            severity=data.severity,
            sentiment=data.sentiment,
            emotion=data.emotion,
            ticket_status=data.ticket_status,
            ai_decision=data.ai_decision,
            ai_draft_reply=data.ai_draft_reply,
            forwarded_to=data.forwarded_to,
        )
        session.add(new_ticket)
        session.commit()
        session.refresh(new_ticket)
        return {"status": "success", "ticket": _ticket_row(new_ticket)}


# ---------------------------------------------------------------------------
# Tickets — update (applies to latest row; status/severity/routing propagate)
# ---------------------------------------------------------------------------

@app.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, data: TicketUpdate):
    with Session(engine) as session:
        rows = (
            session.query(Ticket)
            .filter(Ticket.ticket_id == ticket_id)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Apply status / severity / routing to ALL rows in the thread
        for row in rows:
            if data.ticket_status is not None:
                row.ticket_status = data.ticket_status
            if data.severity is not None:
                row.severity = data.severity
            if data.forwarded_to is not None:
                row.forwarded_to = data.forwarded_to

        # Apply message-specific fields only to the latest row
        latest = max(rows, key=lambda r: r.id)
        if data.customer_email is not None:
            latest.customer_email = data.customer_email
        if data.subject is not None:
            latest.subject = data.subject
        if data.body is not None:
            latest.body = data.body
        if data.message_id is not None:
            latest.message_id = data.message_id
        if data.thread_id is not None:
            latest.thread_id = data.thread_id
        if data.issue is not None:
            latest.issue = data.issue
        if data.sentiment is not None:
            latest.sentiment = data.sentiment
        if data.emotion is not None:
            latest.emotion = data.emotion
        if data.ai_decision is not None:
            latest.ai_decision = data.ai_decision
        if data.ai_draft_reply is not None:
            latest.ai_draft_reply = data.ai_draft_reply

        session.commit()
        return {"status": "success", "ticket": _ticket_row(latest)}


# ---------------------------------------------------------------------------
# Tickets — send draft (approve & send pending AI reply)
# ---------------------------------------------------------------------------

@app.post("/tickets/{ticket_id}/send-draft")
async def send_draft(ticket_id: int, data: TicketSendDraft):
    """
    Send the (optionally edited) AI draft reply to the customer,
    then mark all rows in the ticket thread as Closed.
    """
    with Session(engine) as session:
        rows = (
            session.query(Ticket)
            .filter(Ticket.ticket_id == ticket_id)
            .order_by(Ticket.created_at.asc())
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Ticket not found")

        latest = max(rows, key=lambda r: r.id)
        customer_email = latest.customer_email
        subject = latest.subject or ""
        message_id = latest.message_id or ""

        # Send the reply
        reply_subject = (
            f"[Ticket #{ticket_id}] Re: {subject}"
            if not subject.startswith("Re:") else subject
        )
        try:
            reply_in_thread(customer_email, reply_subject, message_id, data.draft_reply)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

        # Mark all rows closed and set the draft as sent on the latest row
        for row in rows:
            row.ticket_status = "Closed"
        latest.ai_draft_reply = data.draft_reply
        latest.draft_sent = True

        session.commit()

        return {
            "status": "success",
            "message": f"Reply sent to {customer_email} and ticket #{ticket_id} closed.",
        }


# ---------------------------------------------------------------------------
# Tickets — delete (all messages in the thread)
# ---------------------------------------------------------------------------

@app.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int):
    with Session(engine) as session:
        rows = (
            session.query(Ticket)
            .filter(Ticket.ticket_id == ticket_id)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Ticket not found")
        for row in rows:
            session.delete(row)
        session.commit()
        return {"status": "success", "ticket_id": ticket_id, "deleted_rows": len(rows)}


# ---------------------------------------------------------------------------
# Health & Polling checks
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_endpoint(response: Response):
    db_status = check_database_health()
    pinecone_status = check_pinecone_health()
    gemini_status = check_gemini_health()
    imap_status = check_email_imap_health()
    smtp_status = check_email_smtp_health()

    all_healthy = (
        db_status["status"] == "healthy"
        and pinecone_status["status"] == "healthy"
        and gemini_status["status"] == "healthy"
        and imap_status["status"] == "healthy"
        and smtp_status["status"] == "healthy"
    )

    status = "healthy" if all_healthy else "unhealthy"
    if not all_healthy:
        response.status_code = 503

    return {
        "status": status,
        "services": {
            "database": db_status,
            "pinecone": pinecone_status,
            "gemini_api": gemini_status,
            "email_imap": imap_status,
            "email_smtp": smtp_status
        }
    }


@app.get("/poll-check")
async def poll_check_endpoint():
    print("polling")
    return {"status": "ok"}