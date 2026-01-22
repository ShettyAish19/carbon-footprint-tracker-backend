from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import UserStats, Activity

def calculate_points(daily_co2: float) -> int:
    if daily_co2 <= 5:
        return 10
    elif daily_co2 <= 10:
        return 5
    return 0

def update_user_stats(db: Session, user_id: str):
    today = datetime.utcnow().date()

    # Calculate today's total CO2
    activities = (
        db.query(Activity)
        .filter(
            Activity.user_id == user_id,
            Activity.created_at >= datetime.combine(today, datetime.min.time())
        )
        .all()
    )

    daily_co2 = sum(float(a.co2_kg) for a in activities)
    points = calculate_points(daily_co2)

    # Get yesterday's stats (for streak)
    yesterday = today - timedelta(days=1)
    prev = (
        db.query(UserStats)
        .filter(UserStats.user_id == user_id)
        .order_by(UserStats.date.desc())
        .first()
    )

    streak = 1
    if prev and prev.date.date() == yesterday:
        if daily_co2 <= prev.daily_co2_kg:
            streak = prev.streak + 1

    # Upsert today's stats
    existing = (
        db.query(UserStats)
        .filter(UserStats.user_id == user_id, UserStats.date == today)
        .first()
    )

    if existing:
        existing.daily_co2_kg = daily_co2
        existing.points = points
        existing.streak = streak
    else:
        db.add(UserStats(
            user_id=user_id,
            date=datetime.combine(today, datetime.min.time()),
            daily_co2_kg=daily_co2,
            points=points,
            streak=streak
        ))

    db.commit()
