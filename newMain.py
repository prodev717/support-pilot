import os
import imaplib
import smtplib
import email
import time
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from dotenv import load_dotenv
from google import genai
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


client = genai.Client(api_key=GEMINI_API_KEY)

def clean_header(header_value):
    if not header_value:
        return ""
    decoded, encoding = decode_header(header_value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding if encoding else "utf-8", errors="ignore")
    return str(decoded)


def load_policy():
    with open("policy.txt", "r", encoding="utf-8") as f:
        return f.read()


def get_email_body(msg):
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                continue

            if content_type in ["text/plain", "text/html"]:
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    if body:
                        return body
                except:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        except:
            body = ""

    return body.strip()


def generate_reply(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


def reply_in_thread(to_email, original_subject, msg_id, body_text):
    reply = EmailMessage()
    reply.set_content(body_text)

    reply["Subject"] = (
        f"Re: {original_subject}"
        if not original_subject.startswith("Re:")
        else original_subject
    )
    reply["From"] = EMAIL_USER
    reply["To"] = to_email
    reply["In-Reply-To"] = msg_id
    reply["References"] = msg_id

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(reply)

        print(f"Sent reply to {to_email}")

    except Exception as e:
        print(f"Failed to send reply: {e}")


def process_inbox():
    if not EMAIL_USER or not EMAIL_PASS:
        print("Missing credentials in .env file.")
        return

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

    print(f"Found {len(email_ids)} unread emails.")

    blocked_keywords = [
        "no-reply",
        "noreply",
        "mailer-daemon",
        "notification",
        "notifications"
    ]

    policy = load_policy()

    for e_id in email_ids:
        res, msg_data = mail.fetch(e_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                sender_name, sender_email = parseaddr(msg["From"])
                subject = clean_header(msg["Subject"] or "")
                message_id = msg.get("Message-ID")

                print(f"\nProcessing email from: {sender_email}")

                # Skip self emails
                if EMAIL_USER.lower() == sender_email.lower():
                    print("Skipping self email.")
                    continue

                # Skip automated emails
                if any(keyword in sender_email.lower() for keyword in blocked_keywords):
                    print(f"Skipping automated email from {sender_email}")
                    continue

                # Extract email body
                email_text = get_email_body(msg)

                # Skip empty emails
                if len(email_text.strip()) < 10:
                    print("Skipping empty/invalid email")
                    continue

                
                prompt = f"""
SYSTEM POLICY:
{policy}

CUSTOMER EMAIL:
{email_text}

TASK:
Write a short professional support reply strictly following company policies.
"""

                
                reply_body = generate_reply(prompt)

               
                if sender_email and message_id:
                    reply_in_thread(sender_email, subject, message_id, reply_body)
                    mail.store(e_id, "+FLAGS", "\\Seen")
                else:
                    print("Skipping email: Missing sender or Message-ID header.")

    mail.close()
    mail.logout()


if __name__ == "__main__":
    while True:
        print("Checking inbox for unseen emails...")
        process_inbox()
        time.sleep(60)
