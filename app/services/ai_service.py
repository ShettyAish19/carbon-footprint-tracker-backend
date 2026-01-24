# from typing import List, Dict, Any
# import os, json, time
# from dotenv import load_dotenv
# from app.db.session import SessionLocal
# from app.db.models import Activity, UserStats
# from datetime import datetime, timedelta

# load_dotenv()
# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
# load_dotenv(os.path.join(BASE_DIR, ".env"))

# # ------------------------------
# # Fallback Suggestions
# # ------------------------------

# def rule_based_suggestions(activity: Dict[str, Any]) -> List[Dict[str,Any]]:
#     suggestions = []
#     typ = activity.get("type")
#     if typ == "travel":
#         d = float(activity.get("distance_km") or 0)
#         suggestions.append({"text": f"Reduce short trips under {int(max(2,d))} km by walking or cycling.", "difficulty":"easy"})
#     elif typ == "electricity":
#         suggestions.append({"text":"Unplug idle devices to reduce daily electricity use.","difficulty":"easy"})
#     elif typ == "food":
#         suggestions.append({"text":"Add more plant-based meals this week.","difficulty":"easy"})
#     if not suggestions:
#         suggestions.append({"text":"Reduce waste and save energy where possible.","difficulty":"easy"})
#     return suggestions

# # ------------------------------
# # User Context
# # ------------------------------

# def get_user_context(user_id: str) -> dict:
#     db = SessionLocal()
#     now = datetime.utcnow()
#     week_ago = now - timedelta(days=7)

#     rows = db.query(Activity).filter(
#         Activity.user_id == user_id,
#         Activity.created_at >= week_ago
#     ).all()

#     total = sum(float(r.co2_kg) for r in rows)
#     avg_daily = round(total / max(1,7),2)

#     type_totals = {}
#     for r in rows:
#         type_totals[r.type] = type_totals.get(r.type,0)+float(r.co2_kg)

#     top_type = max(type_totals, key=type_totals.get) if type_totals else "travel"

#     stat = db.query(UserStats).filter(UserStats.user_id==user_id).order_by(UserStats.date.desc()).first()

#     ctx = {
#         "avg_daily_7d": avg_daily,
#         "top_activity_type": top_type,
#         "streak": stat.streak if stat else 0,
#         "points": stat.points if stat else 0
#     }
#     db.close()
#     return ctx

# # ------------------------------
# # Gemini Config
# # ------------------------------

# USE_GEMINI = False
# MODEL = os.getenv("GEMINI_MODEL","gemini-2.5-flash")

# def call_gemini(prompt: str) -> str:
#     try:
#         from google import genai
#         client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#         resp = client.models.generate_content(
#             model=MODEL,
#             contents=prompt,
#             config={"temperature":0.0,"max_output_tokens":150}
#         )
#         return resp.text if hasattr(resp,"text") else ""
#     except Exception as e:
#         print("Gemini failed:",e)
#         return ""

# # ------------------------------
# # Prompt (Same Style, Safer)
# # ------------------------------

# def build_prompt(activity: dict, user_ctx: dict) -> str:
#     return f"""
# Return ONLY valid JSON.
# No markdown. No explanation.

# Format:
# [
#   {{ "text": "...", "difficulty": "easy|medium|hard" }},
#   {{ "text": "...", "difficulty": "easy|medium|hard" }}
# ]

# At most 2 items.
# Each text under 18 words.

# User:
# - Avg 7d: {user_ctx.get("avg_daily_7d")}
# - Top: {user_ctx.get("top_activity_type")}
# - Streak: {user_ctx.get("streak")}
# - Points: {user_ctx.get("points")}

# Activity:
# {json.dumps(activity, default=str)}
# """

# # ------------------------------
# # Robust Parser
# # ------------------------------

# def parse_model_output(text: str) -> List[Dict[str,Any]]:
#     if not text:
#         return []
#     t = text.strip()
#     # Try full JSON
#     try:
#         data = json.loads(t)
#         if isinstance(data, dict): data=[data]
#         return [{"text":x.get("text"),"difficulty":x.get("difficulty","medium")}
#                 for x in data if isinstance(x,dict) and "text" in x]
#     except:
#         pass
#     # Salvage first object
#     try:
#         s = t.find("{")
#         e = t.find("}")
#         if s!=-1 and e!=-1 and e>s:
#             obj = json.loads(t[s:e+1])
#             return [{"text":obj.get("text"),"difficulty":obj.get("difficulty","medium")}]
#     except:
#         pass
#     return []

# # ------------------------------
# # Main Entry
# # ------------------------------

# def generate_suggestions_for_activity(activity: Dict[str,Any]) -> List[Dict[str,Any]]:
#     user_id = activity.get("user_id")
#     user_ctx = get_user_context(user_id) if user_id else {}

#     if USE_GEMINI:
#         for _ in range(2):   # retry once
#             prompt = build_prompt(activity, user_ctx)
#             text = call_gemini(prompt)
#             parsed = parse_model_output(text)
#             if parsed:
#                 return parsed

#     return rule_based_suggestions(activity)



# (Cloud)backend/app/services/ai_service.py

from typing import List, Dict, Any
import os, json
from dotenv import load_dotenv
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.db.models import Activity, UserStats

# -------------------------------------------------
# Environment
# -------------------------------------------------

load_dotenv()
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

USE_GEMINI = True   # ✅ turn ON only when quota allows
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# -------------------------------------------------
# FALLBACK RULE-BASED SUGGESTIONS
# -------------------------------------------------

def rule_based_suggestions(activity: Dict[str, Any]) -> List[Dict[str, Any]]:
    suggestions = []
    typ = activity.get("type")

    # -----------------------
    # TRAVEL
    # -----------------------
    if typ == "travel":
        mode = (activity.get("mode") or "").lower()
        d = float(activity.get("distance_km") or 0)

        if mode in ["bike", "bicycle", "cycle"]:
            suggestions.append({
                "text": f"Cycling for {d:.1f} km is a low-carbon choice. Keep using it for short daily trips.",
                "difficulty": "easy"
            })
            suggestions.append({
                "text": "You could replace another short trip this week with cycling to maintain this habit.",
                "difficulty": "easy"
            })

        elif mode == "walk":
            suggestions.append({
                "text": "Walking produces almost zero emissions. Consider using it for all trips under 2 km.",
                "difficulty": "easy"
            })

        elif mode == "train":
            suggestions.append({
                "text": f"Train travel has lower emissions per km. Continue using it for medium-distance travel.",
                "difficulty": "easy"
            })

        elif mode == "bus":
            suggestions.append({
                "text": "Public transport reduces per-person emissions. Prefer buses over private vehicles when possible.",
                "difficulty": "easy"
            })

        elif mode in ["car", "motorbike"]:
            if d <= 5:
                suggestions.append({
                    "text": f"For trips under {int(d)} km, walking or cycling could fully avoid emissions.",
                    "difficulty": "easy"
                })
            elif d <= 15:
                suggestions.append({
                    "text": "For medium trips, carpooling or public transport can reduce emissions significantly.",
                    "difficulty": "medium"
                })
            else:
                suggestions.append({
                    "text": "For long trips, combining errands into one journey can lower total emissions.",
                    "difficulty": "medium"
                })

    # -----------------------
    # ELECTRICITY
    # -----------------------
    elif typ == "electricity":
        kwh = float(activity.get("kwh") or 0)

        if kwh <= 2:
            suggestions.append({
                "text": "Your electricity usage is relatively low. Continue switching off unused devices.",
                "difficulty": "easy"
            })
        elif kwh <= 6:
            suggestions.append({
                "text": "Reducing standby power and using LED lighting can cut daily electricity usage.",
                "difficulty": "easy"
            })
        else:
            suggestions.append({
                "text": "High electricity usage detected. Limiting AC usage and unplugging idle devices can help.",
                "difficulty": "medium"
            })

    # -----------------------
    # FOOD
    # -----------------------
    elif typ == "food":
        cat = (activity.get("food_category") or "").lower()

        if cat == "veg":
            suggestions.append({
                "text": "Vegetarian meals have lower carbon impact. Maintaining this diet reduces emissions.",
                "difficulty": "easy"
            })
            suggestions.append({
                "text": "You could explore locally sourced vegetables to reduce transport emissions further.",
                "difficulty": "easy"
            })

        elif cat == "chicken":
            suggestions.append({
                "text": "Chicken has lower emissions than red meat. Replacing some meals with vegetarian options helps more.",
                "difficulty": "medium"
            })

        elif cat == "beef":
            suggestions.append({
                "text": "Beef has a high carbon footprint. Replacing even one meal with plant-based food helps.",
                "difficulty": "hard"
            })

    # -----------------------
    # FALLBACK
    # -----------------------
    if not suggestions:
        suggestions.append({
            "text": "Small daily choices like saving energy and reducing travel add up over time.",
            "difficulty": "easy"
        })

    return suggestions[:2]  # always return max 2


# -------------------------------------------------
# USER CONTEXT (PERSONALIZATION)
# -------------------------------------------------

def get_user_context(user_id: str) -> dict:
    db = SessionLocal()
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    activities = db.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.created_at >= week_ago
    ).all()

    total = sum(float(a.co2_kg) for a in activities)
    avg_daily = round(total / 7, 2)

    by_type = {}
    for a in activities:
        by_type[a.type] = by_type.get(a.type, 0) + float(a.co2_kg)

    top_type = max(by_type, key=by_type.get) if by_type else "travel"

    stats = (
        db.query(UserStats)
        .filter(UserStats.user_id == user_id)
        .order_by(UserStats.date.desc())
        .first()
    )

    ctx = {
        "avg_daily_7d": avg_daily,
        "top_activity_type": top_type,
        "streak": stats.streak if stats else 0,
        "points": stats.points if stats else 0,
    }

    db.close()
    return ctx

# -------------------------------------------------
# GEMINI CALL (SINGLE ATTEMPT ONLY)
# -------------------------------------------------

def call_gemini(prompt: str) -> str:
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "temperature": 0.0,
                "max_output_tokens": 150
            }
        )

        return response.text if hasattr(response, "text") else ""

    except Exception as e:
        print("Gemini failed:", e)
        return ""

# -------------------------------------------------
# PROMPT (SAFE & SHORT)
# -------------------------------------------------

def build_prompt(activity: dict, user_ctx: dict) -> str:
    return f"""
Return ONLY valid JSON. No markdown.

Format:
[
  {{ "text": "...", "difficulty": "easy|medium|hard" }}
]

Max 2 items. Each text under 18 words.

User:
- Avg 7d CO2: {user_ctx.get("avg_daily_7d")}
- Top source: {user_ctx.get("top_activity_type")}
- Streak: {user_ctx.get("streak")}
- Points: {user_ctx.get("points")}

Activity:
{json.dumps(activity, default=str)}
"""

# -------------------------------------------------
# PARSER (FAIL-SAFE)
# -------------------------------------------------

def parse_model_output(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]

        return [
            {
                "text": d.get("text"),
                "difficulty": d.get("difficulty", "medium")
            }
            for d in data if isinstance(d, dict) and "text" in d
        ]
    except Exception:
        return []

# -------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------

def generate_suggestions_for_activity(activity: Dict[str, Any]) -> List[Dict[str, Any]]:
    user_id = activity.get("user_id")
    user_ctx = get_user_context(user_id) if user_id else {}

    
    # Do NOT call Gemini again if already attempted
    if USE_GEMINI and not activity.get("ai_attempted"):
        prompt = build_prompt(activity, user_ctx)
        text = call_gemini(prompt)
        parsed = parse_model_output(text)
        if parsed:
            return parsed


    return rule_based_suggestions(activity)
