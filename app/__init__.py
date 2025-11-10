from fastapi import FastAPI
from .config import settings
from .database import engine, Base

def create_app():
    app = FastAPI(
        title="Email Service"
        description="Microservice for email template processing and delivery",
        version="1.0.0"
    )


    # Create database tables
    Base.metadata.create_all(bind=engine)

    return app