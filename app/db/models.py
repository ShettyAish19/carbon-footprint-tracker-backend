# backend/app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from passlib.context import CryptContext

Base = declarative_base()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    type = Column(String, index=True)
    mode = Column(String, nullable=True)
    distance_km = Column(Float, nullable=True)
    kwh = Column(Float, nullable=True)
    food_category = Column(String, nullable=True)
    co2_kg = Column(Float, nullable=False)
    calculation_source = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    meta = Column(JSON, nullable=True)

class Suggestion(Base):
    __tablename__ = "suggestions"
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, nullable=True)                # link to Activity (optional)
    user_id = Column(String, index=True)
    suggestion_text = Column(Text, nullable=False)
    est_saving_kg = Column(Float, nullable=True)
    difficulty = Column(String, nullable=True)                  # easy/medium/hard
    source = Column(String, nullable=False, default="fallback") # 'fallback' or 'ai'
    created_at = Column(DateTime, default=datetime.utcnow)
    meta = Column(JSON, nullable=True)

class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)

    daily_co2_kg = Column(Float, nullable=False)
    points = Column(Integer, default=0)
    streak = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

