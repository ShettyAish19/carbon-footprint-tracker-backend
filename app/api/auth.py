from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.session import SessionLocal
from app.db.crud import create_user, get_user_by_username

router = APIRouter(prefix="/auth")

class RegisterIn(BaseModel):
    username: str
    password: str

class LoginIn(BaseModel):
    username: str
    password: str

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.post("/register")
def register(data: RegisterIn, db=Depends(get_db)):
    if get_user_by_username(db, data.username):
        raise HTTPException(400, "Username already exists")
    user = create_user(db, data.username, data.password)
    return {"id": user.id, "username": user.username}

@router.post("/login")
def login(data: LoginIn, db=Depends(get_db)):
    user = get_user_by_username(db, data.username)
    if not user or not user.verify_password(data.password):
        raise HTTPException(401, "Invalid credentials")
    return {"message": "Login success", "user_id": user.username}
