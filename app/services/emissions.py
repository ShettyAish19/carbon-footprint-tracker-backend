import os
import requests
from functools import lru_cache
from dotenv import load_dotenv

# --------------------------------------------------
# Environment setup
# --------------------------------------------------

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CLIMATIQ_KEY = os.getenv("CLIMATIQ_API_KEY")
CLIMATIQ_URL = "https://beta3.api.climatiq.io/estimate"
TIMEOUT = 8  # seconds

# --------------------------------------------------
# Local fallback emission factors (ONLY FALLBACK)
# --------------------------------------------------

# Travel (kg CO2 per km)
LOCAL_TRAVEL_FACTORS = {
    "car": 0.17,
    "bus": 0.06,
    "train": 0.041,
    "bicycle": 0.0,        
    "motorbike": 0.11     
}

# Electricity (kg CO2 per kWh) — India average
LOCAL_ELECTRICITY_FACTOR = 0.7

# Food (kg CO2 per day / serving approx)
LOCAL_FOOD = {
    "veg": 2.0,
    "chicken": 6.0,
    "beef": 27.0
}

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _headers():
    if CLIMATIQ_KEY:
        return {
            "Authorization": f"Bearer {CLIMATIQ_KEY}",
            "Content-Type": "application/json"
        }
    return {"Content-Type": "application/json"}

# --------------------------------------------------
# Emission estimators
# --------------------------------------------------

@lru_cache(maxsize=1024)
def estimate_travel(mode: str, distance_km: float) -> float:
    mode = (mode or "car").lower()

    # Fallback
    if not CLIMATIQ_KEY:
        factor = LOCAL_TRAVEL_FACTORS.get(mode)
        if factor is None:
            raise ValueError(f"Unsupported travel mode: {mode}")
        return distance_km * factor

    payload = {
        "emission_factor": {
            "activity_id": "passenger_vehicle-vehicle_type_car-fuel_source_petrol-distance_km"
        },
        "parameters": {
            "distance": distance_km,
            "distance_unit": "km"
        }
    }

    try:
        r = requests.post(CLIMATIQ_URL, json=payload, headers=_headers(), timeout=TIMEOUT)
        if r.ok:
            data = r.json()
            if "co2e" in data:
                return float(data["co2e"])
    except Exception:
        pass

    # Fallback if API fails
    return distance_km * LOCAL_TRAVEL_FACTORS.get(mode, LOCAL_TRAVEL_FACTORS["car"])


@lru_cache(maxsize=1024)
def estimate_electricity(kwh: float, country: str = None) -> float:
    if not CLIMATIQ_KEY:
        return kwh * LOCAL_ELECTRICITY_FACTOR

    payload = {
        "emission_factor": {"activity_id": "electricity-energy_source_grid_mix-energy_unit_kwh"},
        "parameters": {
            "energy": kwh,
            "energy_unit": "kWh",
            "country": country
        }
    }

    try:
        r = requests.post(CLIMATIQ_URL, json=payload, headers=_headers(), timeout=TIMEOUT)
        if r.ok:
            data = r.json()
            if "co2e" in data:
                return float(data["co2e"])
    except Exception:
        pass

    return kwh * LOCAL_ELECTRICITY_FACTOR


@lru_cache(maxsize=1024)
def estimate_food(category: str) -> float:
    category = (category or "veg").lower()

    # Using only fallback for now (Climatiq food support can be added later)
    return LOCAL_FOOD.get(category, LOCAL_FOOD["veg"])
