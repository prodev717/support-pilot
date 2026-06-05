import time
from email_service import process_inbox

if __name__ == "__main__":
    while True:
        print("Checking inbox for unseen emails")
        process_inbox()
        time.sleep(60)