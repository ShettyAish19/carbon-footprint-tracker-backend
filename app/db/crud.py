# backend/app/db/crud.py
from sqlalchemy.orm import Session
from app.db.models import Suggestion, Activity
from datetime import datetime
from sqlalchemy import text
from app.db.models import User

def create_suggestion(db: Session, user_id: str, activity_id: int, text: str,
                      est_saving: float=None, difficulty: str=None, meta: dict=None, source: str="fallback"):
    s = Suggestion(
        activity_id=activity_id,
        user_id=user_id,
        suggestion_text=text,
        est_saving_kg=est_saving,
        difficulty=difficulty,
        meta=meta or {},
        source=source
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def get_suggestions_for_user(db: Session, user_id: str, limit: int=50):
    return db.query(Suggestion).filter(Suggestion.user_id==user_id).order_by(Suggestion.created_at.desc()).limit(limit).all()

def delete_fallback_suggestions_for_activity(db: Session, activity_id: int):
    # remove fallback suggestions for a given activity_id
    try:
        db.execute(text("DELETE FROM suggestions WHERE activity_id = :aid AND source = 'fallback'"), {"aid": activity_id})
        db.commit()
    except Exception as e:
        print("Failed to delete fallback suggestions:", e)



def create_user(db, username: str, password: str):
    hashed = User.hash_password(password)
    user = User(username=username, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db, username: str):
    return db.query(User).filter(User.username == username).first()
