from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import activities
from app.api import suggestions,summary
from app.api import gamification
from app.api import auth

from app.api import stats




app = FastAPI(title="Carbon Tracker API")

# VERY permissive CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # allow all origins while developing
    allow_credentials=True,
    allow_methods=["*"],            # allow POST/OPTIONS/etc.
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(activities.router, prefix="/activities")
app.include_router(suggestions.router, prefix="/suggestions")
app.include_router(summary.router, prefix="/summary")
app.include_router(gamification.router, prefix="/gamification")
app.include_router(stats.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "carbon-tracker"}