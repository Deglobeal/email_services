import requests
import json

# URL of your running FastAPI service
BASE_URL = "http://127.0.0.1:8000"

# Test payload for sending email
payload = {
    "to_email": "yourrecipient@gmail.com",  # Replace with a real email you can test
    "subject": "Test Email from Python Script",
    "body": "<h1>Hello from FastAPI Email Service!</h1>",
    "request_id": "test123"
}

headers = {
    "Content-Type": "application/json"
}

def test_send_email():
    url = f"{BASE_URL}/send_email"
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

if __name__ == "__main__":
    test_send_email()
