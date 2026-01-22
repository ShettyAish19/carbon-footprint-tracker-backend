# backend/app/api/suggestions.py
from fastapi import APIRouter, Depends
from app.db.session import SessionLocal
from app.db.crud import get_suggestions_for_user
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

class SuggestionOut(BaseModel):
    id: int
    activity_id: int | None
    user_id: str
    suggestion_text: str
    est_saving_kg: float | None
    difficulty: str | None
    source: str
    created_at: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/users/{user_id}", response_model=List[SuggestionOut])
def suggestions_for_user(user_id: str, db=Depends(get_db)):
    rows = get_suggestions_for_user(db, user_id=user_id)
    return rows
