import requests
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
# IMPORTANT: If this is None, the test will fail with 401 Unauthorized.
# Make sure your .env file has WEBHOOK_SECRET=...
SECRET = os.getenv("WEBHOOK_SECRET","my_docker_secret_key") 
if not SECRET:
    print("⚠️ WARNING: WEBHOOK_SECRET not found in environment variables.")
    SECRET = "default_secret_for_testing" # Fallback matching the server default

URL = "http://127.0.0.1:8000/webhook"

# --- 1. PAYLOAD ---
payload = {
    "message_id": "msg_9999", # Change this ID to test idempotency!
    "from": "+14155552671",
    "to": "+14155550000",
    "ts": "2025-01-29T10:00:00Z",
    "text": "Hello! Testing logs and metrics."
}

# --- 2. SIGNATURE CALCULATION ---
body_bytes = json.dumps(payload).encode()
signature = hmac.new(
    key=SECRET.encode(),
    msg=body_bytes,
    digestmod=hashlib.sha256
).hexdigest()

# --- 3. SEND ---
headers = {
    "Content-Type": "application/json",
    "X-Signature": signature
}

try:
    print(f"Sending to {URL} with signature {signature[:10]}...")
    response = requests.post(URL, data=body_bytes, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")

except Exception as e:
    print(f"Error: {e}")