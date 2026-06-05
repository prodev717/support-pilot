from pydantic import BaseModel


class EmailCreate(BaseModel):
    department: str
    email: str
    description: str | None = None


class EmailUpdate(BaseModel):
    department: str | None = None
    email: str | None = None
    description: str | None = None


class TicketCreate(BaseModel):
    ticket_id: int | None = None          # If provided, attach message to existing ticket thread
    customer_email: str
    subject: str | None = None
    body: str | None = None
    message_id: str | None = None
    thread_id: str | None = None
    issue: str | None = None
    severity: str | None = None
    sentiment: str | None = None
    emotion: str | None = None
    ticket_status: str | None = "Open"
    ai_decision: str | None = None
    ai_draft_reply: str | None = None
    forwarded_to: str | None = None


class TicketUpdate(BaseModel):
    customer_email: str | None = None
    subject: str | None = None
    body: str | None = None
    message_id: str | None = None
    thread_id: str | None = None
    issue: str | None = None
    severity: str | None = None
    sentiment: str | None = None
    emotion: str | None = None
    ticket_status: str | None = None
    ai_decision: str | None = None
    ai_draft_reply: str | None = None
    forwarded_to: str | None = None


class TicketSendDraft(BaseModel):
    draft_reply: str                      # The (possibly edited) reply text to send
