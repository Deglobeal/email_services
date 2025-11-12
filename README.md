# Email Service - Stage 4 Microservice

A **distributed email service** for the Stage 4 microservices project. It handles asynchronous email delivery via **RabbitMQ**, supports retries with **exponential backoff**, and uses a **circuit breaker** to prevent service overload. Built with **FastAPI** and **Python asyncio**.

---

## 📂 Project Structure

```
email_services/
│
├── app/
│   ├── __init__.py
│   ├── config.py                 # Environment & settings
│   ├── db.py                     # (Optional DB for status tracking)
│   ├── main.py                    # FastAPI app entrypoint
│   ├── models.py                 # DB models (optional)
│   ├── schemas.py                # Request/Response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── email_sender.py       # SMTP sending logic + retries + circuit breaker
│   │   ├── email_service.py      # High-level wrapper for sending emails
│   │   ├── queue_consumer.py     # RabbitMQ consumer
│   │   ├── queue_publisher.py    # Publish messages to email queue
│   │   └── circuit_breaker.py    # Circuit breaker implementation
│   └── utils/
│       ├── __init__.py
│       └── logger.py             # Logging wrapper
├── .env                          # Environment variables
├── Dockerfile                     # Docker image
├── docker-compose.yml             # Optional dev services
├── requirements.txt               # Python dependencies
└── test_email_service.py          # SMTP, RabbitMQ, API tests
```

---

## ⚙️ Environment Variables

Create a `.env` file in the root folder:

```env
# RabbitMQ
RABBITMQ_URL=amqp://user:password@your-rabbitmq-host:5672/

# SMTP (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_FROM="your_email@gmail.com"
USE_REAL_SMTP=True

# Retry & Circuit breaker
MAX_RETRY_ATTEMPTS=5
SMTP_RETRY_DELAY_SECONDS=2

# Redis (Optional)
REDIS_URL=redis://default:password@your-redis-host:6379
```

> **Note:** For Gmail, generate an **App Password** for SMTP.

---

## 🏗 Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd email_services
```

### 2. Create virtual environment & install dependencies

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🏃‍♂️ Running the service locally

### 1. Start FastAPI

```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Start RabbitMQ (if using Docker Compose)

```bash
docker-compose up -d rabbitmq redis
```

### 3. Start the email consumer

```bash
python -m app.services.queue_consumer
```

---

## 🧪 Testing

Run the included test script:

```bash
python test_email_service.py
```

Tests:

1. **SMTP email** – Sends a real test email.
2. **RabbitMQ** – Tests connection and queue.
3. **FastAPI endpoints** – `/health`, `/send_email`, `/status`.

---

## ⚡ FastAPI Endpoints

### 1. Health Check

**GET** `/health`

**Response:**

```json
{
  "status": "ok",
  "service": "email_service"
}
```

---

### 2. Send Email

**POST** `/send_email/`

**Request:**

```json
{
  "to": "recipient_email@gmail.com",
  "subject": "Hello",
  "body": "Email body content",
  "request_id": "unique-request-id"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Email queued for delivery"
}
```

---

### 3. Check Email Status

**POST** `/status/`

**Request:**

```json
{
  "request_id": "unique-request-id"
}
```

**Response:**

```json
{
  "request_id": "unique-request-id",
  "status": "pending"
}
```

> Status can be `pending`, `delivered`, or `failed`.

---

## 🔄 Circuit Breaker & Retry

* **Retries**: Configurable via `MAX_RETRY_ATTEMPTS` in `.env`.
* **Circuit Breaker**: Prevents sending if SMTP fails repeatedly.
* **Exponential Backoff**: Each retry waits 2^attempt seconds.

---

## 🐳 Docker

### 1. Build image

```bash
docker build -t email_service .
```

### 2. Run container

```bash
docker run -d -p 8000:8000 --env-file .env email_service
```

### 3. Using Docker Compose (with RabbitMQ & Redis)

```bash
docker-compose up -d
```

---

## 📦 Dependencies

* FastAPI
* aiosmtplib
* aio_pika
* python-dotenv
* pydantic
* requests

---

## ✅ Features

* Asynchronous email sending via SMTP
* Retry with exponential backoff
* Circuit breaker to prevent overload
* FastAPI endpoints for health/status/send
* RabbitMQ queue for async processing
* Full logging with correlation IDs

---

## 📈 Next Steps / Submission

1. Ensure `.env` has valid SMTP credentials.
2. Run tests with `python test_email_service.py`.
3. Package with Docker for deployment.
4. Submit GitHub repo and prepare diagram for Stage 4 requirements.

