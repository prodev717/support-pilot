import re
import imaplib
import smtplib
import email
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import EMAIL_USER, EMAIL_PASS
from ai_service import analyze_incoming_email
from database import engine, Ticket, Email as EmailRule


# ---------------------------------------------------------------------------
# Email body / header helpers
# ---------------------------------------------------------------------------

def extract_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="ignore")
    return body.strip()


def clean_header(header_value):
    if not header_value:
        return ""
    decoded, encoding = decode_header(header_value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding if encoding else "utf-8", errors="ignore")
    return str(decoded)


# ---------------------------------------------------------------------------
# SMTP helpers
# ---------------------------------------------------------------------------

def send_email(to_email: str, subject: str, body_text: str,
               in_reply_to: str | None = None, references: str | None = None):
    """Send a plain-text email, optionally as a reply in a thread."""
    msg = EmailMessage()
    msg.set_content(body_text)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"  ✉  Sent email to {to_email}")
    except Exception as e:
        print(f"  ✗  Failed to send email to {to_email}: {e}")


def reply_in_thread(to_email: str, original_subject: str, msg_id: str, body_text: str):
    """Reply to a customer inside the same email thread."""
    reply_subject = (
        f"Re: {original_subject}"
        if not original_subject.startswith("Re:")
        else original_subject
    )
    send_email(to_email, reply_subject, body_text, in_reply_to=msg_id, references=msg_id)


def forward_to_department(dept_email: str, ticket_id: int, subject: str,
                           customer_email: str, body_text: str):
    """Forward an escalated ticket to the relevant department."""
    fwd_subject = f"[Escalated Ticket #{ticket_id}] {subject}"
    fwd_body = (
        f"A support ticket has been escalated and requires your attention.\n\n"
        f"Ticket #: {ticket_id}\n"
        f"Customer: {customer_email}\n"
        f"Subject: {subject}\n"
        f"{'─' * 60}\n\n"
        f"{body_text}\n\n"
        f"{'─' * 60}\n"
        f"Please respond to the customer directly or update the ticket in the Support-Pilot dashboard."
    )
    send_email(dept_email, fwd_subject, fwd_body)


# ---------------------------------------------------------------------------
# Ticket thread resolution
# ---------------------------------------------------------------------------

def _get_next_ticket_id(session: Session) -> int:
    """Return max(ticket_id)+1, or 1 if no tickets exist yet."""
    result = session.query(func.max(Ticket.ticket_id)).scalar()
    return (result or 0) + 1


def _resolve_ticket_id(session: Session, subject: str,
                        thread_id: str | None, message_id: str | None) -> int:
    """
    Return the ticket_id this message belongs to.
    Priority:
      1. '[Ticket #NNN]' found in the subject line.
      2. Existing ticket with the same Gmail thread_id.
      3. Existing ticket with a matching message_id (In-Reply-To chain).
      4. Brand-new ticket_id.
    """
    # 1. Subject tag
    m = re.search(r"\[Ticket #(\d+)\]", subject or "")
    if m:
        tid = int(m.group(1))
        existing = session.query(Ticket).filter(Ticket.ticket_id == tid).first()
        if existing:
            print(f"  ↩  Matched ticket #{tid} via subject tag")
            return tid

    # 2. Gmail thread_id
    if thread_id:
        existing = (
            session.query(Ticket)
            .filter(Ticket.thread_id == thread_id)
            .order_by(Ticket.created_at.desc())
            .first()
        )
        if existing:
            print(f"  ↩  Matched ticket #{existing.ticket_id} via thread_id")
            return existing.ticket_id

    # 3. message_id chain (References header)
    if message_id:
        existing = (
            session.query(Ticket)
            .filter(Ticket.message_id == message_id)
            .order_by(Ticket.created_at.desc())
            .first()
        )
        if existing:
            print(f"  ↩  Matched ticket #{existing.ticket_id} via message_id")
            return existing.ticket_id

    # 4. New ticket
    new_id = _get_next_ticket_id(session)
    print(f"  ★  New ticket #{new_id}")
    return new_id


# ---------------------------------------------------------------------------
# Main inbox processing loop
# ---------------------------------------------------------------------------

def process_inbox():
    if not EMAIL_USER or not EMAIL_PASS:
        print("Missing credentials in .env file.")
        return

    # Fetch routing/department rules for the AI
    with Session(engine) as session:
        dept_rules = [
            {"department": r.department, "email": r.email,
             "description": r.description or ""}
            for r in session.query(EmailRule).all()
        ]

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(EMAIL_USER, EMAIL_PASS)
        status, _ = mail.select("inbox")
        if status != "OK":
            print("Failed to open inbox")
            return
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    status, messages = mail.search(None, "UNSEEN")
    email_ids = messages[0].split()
    print(f"Found {len(email_ids)} unread email(s).")

    blocked_keywords = [
        "no-reply", "noreply", "mailer-daemon",
        "notification", "notifications", "community",
        "forum"
    ]

    for e_id in email_ids:
        res, msg_data = mail.fetch(e_id, "(RFC822)")
        for response_part in msg_data:
            if not isinstance(response_part, tuple):
                continue

            msg = email.message_from_bytes(response_part[1])
            _, sender_email = parseaddr(msg["From"])
            subject = clean_header(msg.get("Subject", ""))
            message_id = msg.get("Message-ID", "").strip()
            thread_id = msg.get("X-GM-THRID") or msg.get("Thread-Index") or None
            references = msg.get("References", "")

            print(f"\nProcessing: {sender_email} — {subject}")

            # Skip own / automated emails
            if EMAIL_USER.lower() == sender_email.lower():
                print("  Skipping self-email.")
                continue
            if any(kw in sender_email.lower() for kw in blocked_keywords):
                print(f"  Skipping automated email from {sender_email}")
                continue
            if not sender_email or not message_id:
                print("  Skipping: missing sender or Message-ID.")
                continue

            email_body = extract_email_body(msg)
            if not email_body:
                print("  Skipping empty email body.")
                continue

            # ----------------------------------------------------------
            # AI Decision Engine
            # ----------------------------------------------------------
            try:
                analysis = analyze_incoming_email(subject, email_body, dept_rules)
            except Exception as e:
                print(f"  AI analysis error: {e}")
                analysis = {
                    "issue": "other", "severity": "medium",
                    "sentiment": "neutral", "emotion": "neutral",
                    "ai_decision": "review_required",
                    "explanation": str(e),
                    "forward_to_email": None,
                    "draft_reply": "",
                }

            decision = analysis["ai_decision"]
            print(f"  Decision: {decision.upper()} — {analysis['explanation']}")

            # ----------------------------------------------------------
            # Persist the ticket row
            # ----------------------------------------------------------
            with Session(engine) as session:
                ticket_id = _resolve_ticket_id(
                    session, subject, thread_id, references or message_id
                )

                # Map decision to status
                status_map = {
                    "auto_resolve": "Closed",
                    "review_required": "Pending",
                    "escalate": "Escalated",
                }
                ticket_status = status_map.get(decision, "Open")

                new_row = Ticket(
                    ticket_id=ticket_id,
                    customer_email=sender_email,
                    subject=subject,
                    body=email_body,
                    message_id=message_id,
                    thread_id=thread_id,
                    issue=analysis["issue"],
                    severity=analysis["severity"],
                    sentiment=analysis["sentiment"],
                    emotion=analysis["emotion"],
                    ticket_status=ticket_status,
                    ai_decision=f"{decision}: {analysis['explanation']}",
                    ai_draft_reply=analysis["draft_reply"],
                    forwarded_to=analysis["forward_to_email"],
                )
                session.add(new_row)
                session.commit()
                print(f"Ticket #{ticket_id} saved (status={ticket_status})")

            # ----------------------------------------------------------
            # Post-decision actions
            # ----------------------------------------------------------
            if decision == "auto_resolve":
                reply_subject = (
                    f"[Ticket #{ticket_id}] Re: {subject}"
                    if not subject.startswith("Re:") else subject
                )
                reply_in_thread(sender_email, reply_subject, message_id,
                                analysis["draft_reply"])

            elif decision == "escalate":
                dept_email = analysis.get("forward_to_email")
                if dept_email:
                    forward_to_department(
                        dept_email, ticket_id, subject, sender_email, email_body
                    )
                    # Notify the customer
                    notify_body = (
                        f"Dear Customer,\n\n"
                        f"Thank you for contacting Support-Pilot.\n\n"
                        f"Your request (Ticket #{ticket_id}) has been reviewed and escalated "
                        f"to our specialist team, who will be in touch with you shortly.\n\n"
                        f"Best regards,\nTeam Support-Pilot"
                    )
                    reply_in_thread(sender_email, f"[Ticket #{ticket_id}] Re: {subject}",
                                    message_id, notify_body)
                else:
                    print("Escalate decision but no forward_to_email — treating as Pending.")

            elif decision == "review_required":
                # No email sent — draft stored for human review in the dashboard
                print(f"Draft saved for Ticket #{ticket_id}, awaiting human approval.")
            
            mail.store(e_id, "+FLAGS", "\\Seen")

    mail.close()
    mail.logout()


def check_email_imap_health() -> dict:
    """Check IMAP connection and login health."""
    if not EMAIL_USER or not EMAIL_PASS:
        return {"status": "unhealthy", "error": "Email credentials missing"}
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=10)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.logout()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_email_smtp_health() -> dict:
    """Check SMTP connection and login health."""
    if not EMAIL_USER or not EMAIL_PASS:
        return {"status": "unhealthy", "error": "Email credentials missing"}
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

