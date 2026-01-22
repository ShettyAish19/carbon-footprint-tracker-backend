from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import os

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.db.models import Activity
from app.db.crud import create_suggestion

from app.services.messaging import publish_activity
from app.services.ai_service import rule_based_suggestions
from app.services.emissions import (
    estimate_travel,
    estimate_electricity,
    estimate_food
)

# --------------------------------------------------
# Router & DB init
# --------------------------------------------------

router = APIRouter()
init_db()

# --------------------------------------------------
# Request / Response Schemas
# --------------------------------------------------

class ActivityIn(BaseModel):
    user_id: str
    type: str = Field(..., description="travel | electricity | food")

    mode: Optional[str] = None
    distance_km: Optional[float] = None
    kwh: Optional[float] = None
    food_category: Optional[str] = None

    date: Optional[datetime] = None
    meta: Optional[dict] = None


class ActivityOut(BaseModel):
    activity_id: int
    co2_kg: float
    calculation_source: str


class ActivityOutFull(BaseModel):
    id: int
    user_id: str
    type: str
    mode: Optional[str]
    distance_km: Optional[float]
    kwh: Optional[float]
    food_category: Optional[str]
    co2_kg: float
    calculation_source: str
    created_at: datetime

# --------------------------------------------------
# DB Dependency
# --------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------
# Create Activity
# --------------------------------------------------

@router.post("/", response_model=ActivityOut)
def create_activity(
    payload: ActivityIn,
    db: Session = Depends(get_db)
):
    """
    Create a user activity and calculate CO2 emissions.
    """

    # -----------------------------
    # Validation + Emission Calc
    # -----------------------------

    if payload.type == "travel":
        if payload.mode is None or payload.distance_km is None:
            raise HTTPException(
                status_code=400,
                detail="travel requires mode and distance_km"
            )

        co2 = estimate_travel(payload.mode, payload.distance_km)

    elif payload.type == "electricity":
        if payload.kwh is None:
            raise HTTPException(
                status_code=400,
                detail="electricity requires kwh"
            )

        co2 = estimate_electricity(payload.kwh)

    elif payload.type == "food":
        category = (payload.food_category or "veg").lower()
        co2 = estimate_food(category)

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid activity type"
        )

    calculation_source = (
        "climatiq"
        if os.getenv("CLIMATIQ_API_KEY")
        else "local_factors"
    )

    # -----------------------------
    # Persist Activity
    # -----------------------------

    db_item = Activity(
        user_id=payload.user_id,
        type=payload.type,
        mode=payload.mode,
        distance_km=payload.distance_km,
        kwh=payload.kwh,
        food_category=payload.food_category,
        co2_kg=round(co2, 4),
        calculation_source=calculation_source,
        meta=payload.meta or {}
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # -----------------------------
    # Immediate Rule-Based Suggestions
    # -----------------------------

    try:
        fallback_suggestions = rule_based_suggestions({
            "user_id": db_item.user_id,
            "type": db_item.type,
            "mode": db_item.mode,
            "distance_km": db_item.distance_km,
            "kwh": db_item.kwh,
            "food_category": db_item.food_category,
            "co2_kg": db_item.co2_kg
        })

        for s in fallback_suggestions:
            create_suggestion(
                db=db,
                user_id=db_item.user_id,
                activity_id=db_item.id,
                text=s.get("text"),
                est_saving=s.get("est_saving_kg"),
                difficulty=s.get("difficulty"),
                meta={"stage": "fallback"},
                source="fallback"
            )

    except Exception as e:
        print("Failed to create fallback suggestions:", e)

    # -----------------------------
    # Publish to RabbitMQ
    # -----------------------------

    payload_for_queue = {
        "activity_id": db_item.id,
        "user_id": db_item.user_id,
        "type": db_item.type,
        "mode": db_item.mode,
        "distance_km": db_item.distance_km,
        "kwh": db_item.kwh,
        "co2_kg": float(db_item.co2_kg),
        "created_at": db_item.created_at.isoformat()
    }

    published = publish_activity(payload_for_queue)
    if not published:
        print("Failed to publish activity:", db_item.id)

    return {
        "activity_id": db_item.id,
        "co2_kg": db_item.co2_kg,
        "calculation_source": db_item.calculation_source
    }

# --------------------------------------------------
# List Activities
# --------------------------------------------------

@router.get("/", response_model=List[ActivityOutFull])
def list_activities(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List recent activities.
    """
    return (
        db.query(Activity)
        .order_by(Activity.created_at.desc())
        .limit(limit)
        .all()
    )
