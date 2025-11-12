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
