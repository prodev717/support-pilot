import os
import imaplib
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

print("USER:", EMAIL_USER)
print("PASS LENGTH:", len(EMAIL_PASS))

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)

    response = mail.login(EMAIL_USER, EMAIL_PASS)

    print("SUCCESS:", response)

    mail.logout()

except Exception as e:
    print("ERROR:", e)