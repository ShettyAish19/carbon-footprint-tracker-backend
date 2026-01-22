# backend/app/api/summary.py
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Activity

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _period_start(period: str) -> datetime:
    now = datetime.utcnow()
    if period == "day":
        return now - timedelta(days=1)
    if period == "week":
        return now - timedelta(weeks=1)
    if period == "month":
        return now - timedelta(days=30)
    return now - timedelta(days=1)

@router.get("/users/{user_id}")
def user_summary(
    user_id: str,
    period: str = Query("day", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    start = _period_start(period)
    rows = (
        db.query(Activity)
        .filter(Activity.user_id == user_id, Activity.created_at >= start)
        .all()
    )

    total = sum(float(r.co2_kg) for r in rows)

    by_type: Dict[str, float] = {}
    by_source: Dict[str, float] = {}
    for r in rows:
        by_type[r.type] = by_type.get(r.type, 0.0) + float(r.co2_kg)
        src = r.calculation_source or "local_factors"
        by_source[src] = by_source.get(src, 0.0) + float(r.co2_kg)

    activity_count = len(rows)

    return {
        "user_id": user_id,
        "period": period,
        "start": start.isoformat(),
        "activity_count": activity_count,
        "total_kg": total,
        "breakdown_by_type": by_type,
        "breakdown_by_source": by_source,
    }
