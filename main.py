import time
import requests
from config import SERVER_URL
from email_service import process_inbox

def ping_poll_check():
    url = f"{SERVER_URL.rstrip('/')}/poll-check"
    try:
        response = requests.get(url, timeout=10)
        print(f"[Poll Check] Status: {response.status_code}, Response: {response.json()}")
    except Exception as e:
        print(f"[Poll Check] Failed to reach server at {url}: {e}")

if __name__ == "__main__":
    while True:
        try:
            ping_poll_check()
            print("Checking inbox...")
            process_inbox()
        except Exception as e:
            print(f"[ERROR] Poller crashed: {e}")
        time.sleep(60)