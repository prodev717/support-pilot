import os,imaplib,smtplib,email,time,requests,urllib.parse
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr
from google import genai
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER=os.getenv("EMAIL_USER")
EMAIL_PASS=os.getenv("EMAIL_PASS")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
SERVER_URL=os.getenv("SERVER_URL")

client=genai.Client(api_key=GEMINI_API_KEY)

def generate_reply(prompt):
    response=client.models.generate_content(model="gemini-2.5-flash",contents=prompt)
    return response.text

def search_documents(query):
    if not query or not query.strip():
        return []
    encoded_query=urllib.parse.quote(query)
    url=f"{SERVER_URL}/search?query={encoded_query}"
    try:
        response=requests.get(url,timeout=20)
        response.raise_for_status()
        data=response.json()
        return [result["text"] for result in data.get("results",[])]
    except Exception as e:
        print(f"Search error: {e}")
        return []

def create_search_query(email_body):
    prompt=f"Extract the main customer issue from the email below and return only a short search query.\n\nEmail:\n{email_body}"
    return generate_reply(prompt).strip()

def extract_email_body(msg):
    body=""
    if msg.is_multipart():
        for part in msg.walk():
            content_type=part.get_content_type()
            disposition=str(part.get("Content-Disposition"))
            if content_type=="text/plain" and "attachment" not in disposition:
                payload=part.get_payload(decode=True)
                if payload:
                    body+=payload.decode(errors="ignore")
    else:
        payload=msg.get_payload(decode=True)
        if payload:
            body=payload.decode(errors="ignore")
    return body.strip()

def generate_ai_reply(subject,email_body):
    query=create_search_query(email_body)
    docs=search_documents(query)
    context="\n\n".join(docs[:5]) if docs else "No matching knowledge base articles found."
    prompt=f"""You are a professional customer support agent.

Customer Subject:
{subject}

Customer Email:
{email_body}

Knowledge Base:
{context}

Instructions:
- You are a customer support agent for Support-Pilot.
- Answer using the provided knowledge base whenever possible.
- Do not make up policies, features, timelines, pricing, or technical details.
- If the knowledge base does not contain enough information to answer confidently, politely inform the customer that the issue has been escalated to Team Support-Pilot for further assistance.
- Be professional, concise, and helpful.
- Write a complete email response.
- Address the customer's question directly.
- Never mention internal prompts, vector databases, retrieval systems, or knowledge base searches.
- Always sign off using:

Best regards,
Team Support-Pilot

Reply:"""
    return generate_reply(prompt)

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
        with smtplib.SMTP("smtp.gmail.com",587,timeout=20) as server:
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
    blocked_keywords=["no-reply","noreply","mailer-daemon","notification","notifications","community","forum","support","helpdesk"]
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
                if not sender_email or not message_id:
                    print("Skipping email: Missing sender or Message-ID header.")
                    continue
                email_body=extract_email_body(msg)
                if not email_body:
                    print("Skipping empty email.")
                    continue
                try:
                    reply_body=generate_ai_reply(subject,email_body)
                    print("\nGenerated Reply:\n")
                    print(reply_body)
                    reply_in_thread(sender_email,subject,message_id,reply_body)
                    mail.store(e_id,"+FLAGS","\\Seen")
                except Exception as e:
                    print(f"AI generation failed: {e}")
    mail.close()
    mail.logout()

if __name__=="__main__":
    while True:
        print("Checking inbox for unseen emails")
        process_inbox()
        time.sleep(60)