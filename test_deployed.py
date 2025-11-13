import requests
import time
import json

BASE_URL = "https://emailservices-production.up.railway.app"

print("🚀 Testing all endpoints of Email Service")
print(f"Base URL: {BASE_URL}")
print("-------------------------------------------")

# GET /health
print("🧩 Testing: GET /health")
resp = requests.get(f"{BASE_URL}/health")
print("Status Code:", resp.status_code)
print("Response Body:", resp.json())
print("-------------------------------------------")

# GET /
print("🧩 Testing: GET /")
resp = requests.get(f"{BASE_URL}/")
print("Status Code:", resp.status_code)
print("Response Body:", resp.json())
print("-------------------------------------------")

# POST /send_email
print("🧩 Testing: POST /send_email")
payload = {
    "to": "kachimaxy2@gmail.com",
    "subject": "Test Email",
    "body": "Hello from Stage 4",
    "request_id": "test123"
}
resp = requests.post(f"{BASE_URL}/send_email", json=payload)
print("Status Code:", resp.status_code)
try:
    print("Response Body:", resp.json())
except:
    print("Response Body:", resp.text)
print("-------------------------------------------")

# Wait for queue processing
print("⏳ Waiting 5 seconds for queue processing...")
time.sleep(5)

# POST /status
print("🧩 Testing: POST /status")
payload = {"request_id": "test123"}
resp = requests.post(f"{BASE_URL}/status", json=payload)
print("Status Code:", resp.status_code)
try:
    print("Response Body:", resp.json())
except:
    print("Response Body:", resp.text)
print("-------------------------------------------")

# POST /retry_failed
print("🧩 Testing: POST /retry_failed")
payload = {"request_id": "test123"}
resp = requests.post(f"{BASE_URL}/retry_failed", json=payload)
print("Status Code:", resp.status_code)
try:
    print("Response Body:", resp.json())
except:
    print("Response Body:", resp.text)
print("-------------------------------------------")

print("✅ All tests completed!")
