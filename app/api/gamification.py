from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import UserStats

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/users/{user_id}")
def get_user_gamification(user_id: str, db: Session = Depends(get_db)):
    stat = (
        db.query(UserStats)
        .filter(UserStats.user_id == user_id)
        .order_by(UserStats.date.desc())
        .first()
    )

    if not stat:
        return {
            "user_id": user_id,
            "points": 0,
            "streak": 0,
            "daily_co2_kg": 0.0
        }

    return {
        "user_id": user_id,
        "date": stat.date,
        "points": stat.points,
        "streak": stat.streak,
        "daily_co2_kg": stat.daily_co2_kg
    }
