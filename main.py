import os
import imaplib
import smtplib
import email
import time
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER=os.getenv("EMAIL_USER")
EMAIL_PASS=os.getenv("EMAIL_PASS")

def clean_header(header_value):
    if not header_value:
        return ""
    decoded,encoding=decode_header(header_value)[0]
    if isinstance(decoded,bytes):
        return decoded.decode(encoding if encoding else "utf-8",errors="ignore")
    return str(decoded)

def reply_in_thread(to_email,original_subject,msg_id,body_text):
    reply=EmailMessage()
    reply.set_content(body_text)
    reply["Subject"]=f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
    reply["From"]=EMAIL_USER
    reply["To"]=to_email
    reply["In-Reply-To"]=msg_id
    reply["References"]=msg_id

    try:
        with smtplib.SMTP("smtp.gmail.com",587,timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER,EMAIL_PASS)
            server.send_message(reply)
        print(f"Sent reply to {to_email}")
    except Exception as e:
        print(f"Failed to send reply: {e}")

def process_inbox():
    if not EMAIL_USER or not EMAIL_PASS:
        print("Missing credentials in .env file.")
        return

    try:
        mail=imaplib.IMAP4_SSL("imap.gmail.com",993)
        mail.login(EMAIL_USER,EMAIL_PASS)

        status,_=mail.select("inbox")

        if status!="OK":
            print("Failed to open inbox")
            return

    except Exception as e:
        print(f"Connection failed: {e}")
        return

    status,messages=mail.search(None,"UNSEEN")
    email_ids=messages[0].split()

    print(f"Found {len(email_ids)} unread emails.")

    blocked_keywords=[
        "no-reply",
        "noreply",
        "mailer-daemon",
        "notification",
        "notifications"
    ]

    for e_id in email_ids:
        res,msg_data=mail.fetch(e_id,"(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part,tuple):
                msg=email.message_from_bytes(response_part[1])

                sender_name,sender_email=parseaddr(msg["From"])
                subject=clean_header(msg["Subject"])
                message_id=msg.get("Message-ID")

                print(f"\nProcessing email from: {sender_email}")

                if EMAIL_USER.lower()==sender_email.lower():
                    print("Skipping self email.")
                    continue

                if any(keyword in sender_email.lower() for keyword in blocked_keywords):
                    print(f"Skipping automated email from {sender_email}")
                    continue

                reply_body="Hello,\n\nYour issue has been noted and logged. Our team will resolve it shortly.\n\nBest regards,\nSupport-Pilot"

                if sender_email and message_id:
                    reply_in_thread(sender_email,subject,message_id,reply_body)
                    mail.store(e_id,"+FLAGS","\\Seen")
                else:
                    print("Skipping email: Missing sender or Message-ID header.")

    mail.close()
    mail.logout()

if __name__=="__main__":
    while True:
        print("Checking inbox for unseen emails")
        process_inbox()
        time.sleep(60)