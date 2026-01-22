# backend/app/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


load_dotenv()  # take environment variables from .env file
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./carbon_dev.db"  # default fallback if no env var set
)

# Determine connect args (sqlite requires special handling)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create tables if they don't exist."""
    from .models import Base
    Base.metadata.create_all(bind=engine)
