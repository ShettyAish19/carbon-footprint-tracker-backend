from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models import Activity, UserStats

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------- Today summary ----------
@router.get("/summary/{user_id}")
def summary(user_id: str, db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    total = db.query(func.sum(Activity.co2_kg)).filter(
        Activity.user_id == user_id,
        func.date(Activity.created_at) == today
    ).scalar()
    return {"today_co2": round(float(total or 0), 2)}

# -------- Gamification stats ----------
@router.get("/user-stats/{user_id}")
def user_stats(user_id: str, db: Session = Depends(get_db)):
    row = db.query(UserStats).filter(
        UserStats.user_id == user_id
    ).order_by(UserStats.date.desc()).first()

    if not row:
        return {"user_id": user_id, "points": 0, "streak": 0}

    return {
        "user_id": row.user_id,
        "points": row.points,
        "streak": row.streak
    }
