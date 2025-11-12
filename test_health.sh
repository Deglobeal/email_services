#!/bin/bash

# ==========================================
# Email Service Endpoint Test Script
# ==========================================
BASE_URL="https://emailservices-production.up.railway.app"
echo "🚀 Testing all endpoints of Email Service"
echo "Base URL: $BASE_URL"
echo "-------------------------------------------"

# Helper function to test endpoints
test_endpoint() {
  local METHOD=$1
  local ENDPOINT=$2
  local PAYLOAD=$3

  echo "🧩 Testing: $METHOD $ENDPOINT"
  if [ "$METHOD" == "GET" ]; then
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}\n" "$BASE_URL$ENDPOINT")
  else
    response=$(curl -s -X "$METHOD" -H "Content-Type: application/json" -d "$PAYLOAD" -w "\nHTTP_STATUS:%{http_code}\n" "$BASE_URL$ENDPOINT")
  fi

  # Extract body and status
  body=$(echo "$response" | sed -e 's/HTTP_STATUS\:.*//g')
  status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

  echo "📦 Response Body: $body"
  echo "🌐 HTTP Status Code: $status"
  echo "-------------------------------------------"
}

# =============================
# 1️⃣ Health Check Endpoint
# =============================
test_endpoint "GET" "/health"

# =============================
# 2️⃣ Root Endpoint
# =============================
test_endpoint "GET" "/"

# =============================
# 3️⃣ Send Email Endpoint
# =============================
SEND_PAYLOAD='{
  "to_email": "example@gmail.com",
  "subject": "Test Email from Railway",
  "body": "This is a test email sent via deployed Email Service."
}'
test_endpoint "POST" "/send_email" "$SEND_PAYLOAD"

# =============================
# 4️⃣ Check Email Status Endpoint
# =============================
STATUS_PAYLOAD='{
  "request_id": "test123"
}'
test_endpoint "POST" "/status" "$STATUS_PAYLOAD"

# =============================
# 5️⃣ Retry Failed Emails Endpoint
# =============================
test_endpoint "POST" "/retry_failed" "{}"

echo "✅ All tests completed!"
