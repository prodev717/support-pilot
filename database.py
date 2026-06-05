import os
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, DateTime, create_engine, func
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL missing")

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


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, nullable=False, index=True)  # logical thread grouping; multiple rows can share this
    customer_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    body = Column(String, nullable=True)
    message_id = Column(String(255), nullable=True)
    thread_id = Column(String(255), nullable=True)
    issue = Column(String(1000), nullable=True)  # question,request,complaint,issue,feedback,cancellation,refund,billing,technical,account,delivery,return,escalation,other
    severity = Column(String(50), nullable=True)  # low,medium,high
    sentiment = Column(String(50), nullable=True)  # positive,neutral,negative,mixed
    emotion = Column(String(50), nullable=True)  # neutral,happy,satisfied,confused,concerned,frustrated,angry,urgent,disappointed,grateful,sad
    ticket_status = Column(String(50), nullable=True, default="Open")  # Open,Closed,Pending,Escalated
    ai_decision = Column(String(1000), nullable=True)  # auto_resolve,review_required,escalate
    ai_draft_reply = Column(String, nullable=True)  # AI-generated draft for review_required tickets
    forwarded_to = Column(String(255), nullable=True)  # if escalated, to which email
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
