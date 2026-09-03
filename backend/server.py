import os
import sys
import time
from collections import defaultdict
import requests
import joblib
import pandas as pd
import datetime
import functools
import jwt
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from twilio.rest import Client
from dotenv import load_dotenv

# Force UTF-8 encoding on Windows console streams if available
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend directory is in python path for clean modular imports
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from database import (
        init_db,
        get_db_connection,
        get_user_by_phone,
        get_user_by_email,
        get_user_by_identifier,
        get_user_by_id,
        create_user,
        update_unverified_user,
        set_user_verification,
        set_email_otp,
        verify_email_otp,
        update_user_credibility,
        get_nearby_shelters,
        get_shelter_by_id,
        create_relief_shelter,
        update_relief_shelter,
        delete_relief_shelter,
        update_shelter_supplies,
        update_shelter_occupancy,
        get_users_in_radius,
        get_nearby_incidents,
        calculate_haversine_distance,
        log_audit_action,
        hash_password,
        verify_password,
        create_incident_report,
        find_nearby_pending_cluster,
        check_and_autoverify_cluster,
        get_active_incident_clusters,
        get_pending_incident_clusters,
        verify_incident_cluster,
        reject_incident_cluster,
        resolve_incident_cluster,
        create_missing_person,
        get_missing_persons,
        get_missing_person_by_id,
        update_missing_person_status,
        create_volunteer_mission,
        get_volunteer_missions,
        update_volunteer_mission_status,
        get_authority_metrics,
        get_database_info
    )
    from alerts import (
        synthesize_bilingual_alert,
        dispatch_multi_channel_alert,
        dispatch_geofenced_sms,
        dispatch_telegram_broadcast,
        generate_whatsapp_broadcast_link,
        get_active_broadcasts,
        generate_cap_xml,
        generate_cap_json
    )
    from vision import analyze_hazard_image
    from routing import calculate_evacuation_route
    from sitrep import generate_sitrep_pdf, generate_sitrep_data
    from mailer import send_verification_email
except ImportError:
    from backend.database import (
        init_db,
        get_db_connection,
        get_user_by_phone,
        get_user_by_email,
        get_user_by_identifier,
        get_user_by_id,
        create_user,
        set_user_verification,
        set_email_otp,
        verify_email_otp,
        update_user_credibility,
        get_nearby_shelters,
        get_shelter_by_id,
        create_relief_shelter,
        update_relief_shelter,
        delete_relief_shelter,
        update_shelter_supplies,
        update_shelter_occupancy,
        get_users_in_radius,
        get_nearby_incidents,
        calculate_haversine_distance,
        log_audit_action,
        hash_password,
        verify_password,
        create_incident_report,
        find_nearby_pending_cluster,
        get_active_incident_clusters,
        get_pending_incident_clusters,
        verify_incident_cluster,
        reject_incident_cluster,
        resolve_incident_cluster,
        create_missing_person,
        get_missing_persons,
        get_missing_person_by_id,
        update_missing_person_status,
        create_volunteer_mission,
        get_volunteer_missions,
        update_volunteer_mission_status,
        get_authority_metrics,
        get_database_info
    )
    from backend.alerts import (
        synthesize_bilingual_alert,
        dispatch_multi_channel_alert,
        dispatch_geofenced_sms,
        dispatch_telegram_broadcast,
        generate_whatsapp_broadcast_link,
        get_active_broadcasts,
        generate_cap_xml,
        generate_cap_json
    )
    from backend.vision import analyze_hazard_image
    from backend.routing import calculate_evacuation_route
    from backend.sitrep import generate_sitrep_pdf, generate_sitrep_data
    from backend.mailer import send_verification_email

# Load local environment variables from .env
load_dotenv()

app = Flask(__name__)

# Configurable CORS origins for production security
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    CORS(app, origins=allowed_origins, supports_credentials=True)
else:
    CORS(app)

# ==========================================================================
# DATABASE INITIALIZATION
# ==========================================================================
try:
    init_db()
    print("[OK] [Database] SQLite Engine & Schema initialized successfully.")
except Exception as db_init_err:
    print(f"[ERROR] [Database] Initialization Warning/Error: {db_init_err}")

# ==========================================================================
# CONFIGURATION & CREDENTIAL MANAGEMENT
# ==========================================================================
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "3b95ffbba2aca9e09b20d0665a788207")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
YOUR_PERSONAL_MOBILE = os.getenv("YOUR_PERSONAL_MOBILE", "+919999900000")

# Enforce JWT_SECRET in production mode
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if os.getenv("FLASK_ENV") == "production":
        raise RuntimeError("CRITICAL: 'JWT_SECRET' environment variable must be set in production mode.")
    JWT_SECRET = "terrarisk_disaster_platform_auth_secret_key_2026_jwt_token_secure"

# ==========================================================================
# ⏱️ RATE LIMITING MIDDLEWARE
# ==========================================================================
RATE_LIMIT_STORE = defaultdict(list)

def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """Enforce sliding-window client IP rate limiting for sensitive endpoints."""
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            if os.getenv("TESTING") == "1":
                return f(*args, **kwargs)
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
            now = time.time()
            key = f"{f.__name__}:{client_ip}"
            
            # Keep timestamps within sliding window
            timestamps = [t for t in RATE_LIMIT_STORE[key] if now - t < window_seconds]
            if len(timestamps) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                return jsonify({
                    "success": False,
                    "error": f"Too many requests. Rate limit reached. Please retry in {retry_after} seconds."
                }), 429
            timestamps.append(now)
            RATE_LIMIT_STORE[key] = timestamps
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Historic Hotspots Array (Kerala Ghats)
HOTSPOTS = [
    {"name": "Chooralmala", "lat": 11.5361, "lng": 76.1667, "desc": "2024 Debris Flow epicenter"},
    {"name": "Mundakkai", "lat": 11.5167, "lng": 76.1500, "desc": "2024 Mass Wasting catastrophe"},
    {"name": "Puthumala", "lat": 11.5583, "lng": 76.1308, "desc": "2019 Hill-collapse zone"},
    {"name": "Kavalappara", "lat": 11.3622, "lng": 76.2411, "desc": "2019 Debris avalanche site"},
    {"name": "Pettimudi", "lat": 10.1600, "lng": 77.0200, "desc": "2020 High-altitude slip"}
]

# ==========================================================================
# 🧠 DUAL-STAGE ML MODEL LOADING
# ==========================================================================
ai_brain = None
rain_brain = None

def _resolve_model_path(model_filename: str) -> str:
    candidate_paths = [
        os.path.join(BACKEND_DIR, "models", model_filename),
        os.path.join(BACKEND_DIR, model_filename),
        os.path.join("models", model_filename),
        os.path.join("backend", "models", model_filename),
        model_filename
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return candidate_paths[0]

classifier_path = _resolve_model_path("landslide_model.pkl")
try:
    if os.path.exists(classifier_path):
        ai_brain = joblib.load(classifier_path)
        print(f"[OK] Status -> Classifier: Loaded from '{classifier_path}'")
    else:
        print(f"[WARNING] landslide_model.pkl not found at {classifier_path}")
except Exception as e:
    print(f"[ERROR] Error loading Classifier: {e}")

regressor_path = _resolve_model_path("rainfall_regressor.pkl")
try:
    if os.path.exists(regressor_path):
        rain_brain = joblib.load(regressor_path)
        print(f"[OK] Status -> Regressor: Loaded from '{regressor_path}'")
    else:
        print(f"[WARNING] rainfall_regressor.pkl not found at {regressor_path}")
except Exception as e:
    print(f"[ERROR] Error loading Regressor: {e}")


# ==========================================================================
# 🔐 JWT AUTHENTICATION & MIDDLEWARE
# ==========================================================================
def generate_jwt_token(user_dict: dict) -> str:
    payload = {
        "user_id": user_dict["id"],
        "phone": user_dict["phone"],
        "role": user_dict["role"],
        "is_verified": user_dict.get("is_verified", 0),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        elif auth_header:
            token = auth_header.strip()
            
        if not token:
            token = request.args.get("token") or (request.json.get("token") if request.is_json and request.json else None)
            
        if not token:
            return jsonify({"success": False, "error": "Authentication token missing in Authorization header"}), 401
            
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({"success": False, "error": "Invalid or expired authorization token"}), 401
            
        current_user = get_user_by_id(payload["user_id"])
        if not current_user:
            if "role" in payload:
                current_user = {
                    "id": payload.get("user_id"),
                    "name": payload.get("name", "User"),
                    "phone": payload.get("phone", ""),
                    "role": payload.get("role", "Citizen"),
                    "is_verified": payload.get("is_verified", 0),
                    "credibility_score": payload.get("credibility_score", 100)
                }
            else:
                return jsonify({"success": False, "error": "User account no longer exists"}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated


def authority_required(f):
    @functools.wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.get("role") not in ("Authority_Admin", "Volunteer"):
            return jsonify({
                "success": False,
                "error": "Access restricted. Action requires Authority Admin or Verified Volunteer credentials."
            }), 403
        return f(current_user, *args, **kwargs)
    return decorated


# ==========================================================================
# 🌐 GEOSPATIAL & WEATHER TELEMETRY HELPERS
# ==========================================================================
# Accurate Kerala Coastline Reference Points (lat, coast_lng)
KERALA_COAST_POINTS = [
    (12.80, 74.85), (12.50, 74.98), (12.00, 75.15), (11.87, 75.35),
    (11.50, 75.60), (11.25, 75.77), (10.80, 75.92), (10.20, 76.15),
    (9.93,  76.26), (9.50,  76.33), (9.00,  76.53), (8.88,  76.58),
    (8.50,  76.92), (8.20,  77.08)
]

# Accurate Kerala Western Ghats Crest / Eastern Border Points (lat, ridge_lng)
KERALA_RIDGE_POINTS = [
    (12.80, 75.35), (12.20, 75.55), (11.80, 76.00), (11.55, 76.25),
    (11.30, 76.50), (11.00, 76.55), (10.75, 76.90), (10.40, 77.00),
    (10.15, 77.15), (9.85,  77.20), (9.50,  77.25), (9.30,  77.18),
    (9.00,  77.22), (8.75,  77.18), (8.40,  77.25), (8.20,  77.28)
]


def _interpolate_polyline_lat(points: list, lat: float) -> float:
    pts = sorted(points, key=lambda p: p[0], reverse=True)
    if lat >= pts[0][0]:
        return pts[0][1]
    if lat <= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        lat1, lng1 = pts[i]
        lat2, lng2 = pts[i+1]
        if lat2 <= lat <= lat1:
            frac = (lat - lat2) / (lat1 - lat2)
            return lng2 + frac * (lng1 - lng2)
    return pts[-1][1]


def resolve_kerala_topography(lat: float, lng: float, elevation: Optional[float] = None) -> tuple:
    """
    Computes true elevation (m), accurate slope angle (degrees), and geological soil type (1, 2, or 3)
    for any coordinate across Kerala based on GSI & KSDMA physiographic classification.
    """
    # 1. Palakkad Gap Break (breaks the Western Ghats between ~10.62°N and 10.90°N)
    in_palakkad_gap = (10.62 <= lat <= 10.90) and (76.25 <= lng <= 76.90)
    
    c_lng = _interpolate_polyline_lat(KERALA_COAST_POINTS, lat)
    r_lng = _interpolate_polyline_lat(KERALA_RIDGE_POINTS, lat)
    width = max(0.05, r_lng - c_lng)
    rel_pos = max(0.0, min(1.0, (lng - c_lng) / width))
    
    # Coordinates in Arabian Sea
    if lng < c_lng - 0.05:
        return 0.0, 0.5, 3
        
    if in_palakkad_gap:
        elev = elevation if (elevation is not None and elevation > 0) else (60.0 + rel_pos * 110.0)
        slope = max(1.5, min(8.5, 2.0 + (rel_pos * 6.5)))
        soil = 2
        return round(elev, 1), round(slope, 1), soil

    # Region Identifiers
    is_idukki = (9.60 <= lat <= 10.35) and (rel_pos >= 0.65)
    is_wayanad = (11.40 <= lat <= 11.95) and (rel_pos >= 0.60)
    is_silent_valley = (10.95 <= lat <= 11.35) and (rel_pos >= 0.65)
    is_south_ghats = (8.40 <= lat <= 9.60) and (rel_pos >= 0.65)
    
    # If high-precision DEM elevation is available
    if elevation is not None and elevation > 0:
        elev = elevation
        if elev < 15.0:
            slope = max(0.5, 0.5 + (elev / 15.0) * 2.5)
            soil = 3
        elif elev < 80.0:
            p = (elev - 15.0) / 65.0
            slope = 3.0 + (p * 5.0)
            soil = 3 if elev < 35.0 else 2
        elif elev < 300.0:
            p = (elev - 80.0) / 220.0
            slope = 8.0 + (p * 11.0)
            soil = 2
        elif elev < 700.0:
            p = (elev - 300.0) / 400.0
            slope = 19.0 + (p * 12.0)
            soil = 1
        elif elev < 1200.0:
            p = (elev - 700.0) / 500.0
            slope = 31.0 + (p * 10.0)
            soil = 1
        else:
            p = min(1.0, (elev - 1200.0) / 1200.0)
            slope = 41.0 + (p * 11.0)
            soil = 1
        return round(elev, 1), round(min(52.0, slope), 1), soil
        
    # Baseline terrain resolution when DEM is offline/pending
    if rel_pos < 0.15:
        # Coastal Lowlands (0 - 15m elev, 0.5 - 3 deg slope)
        elev = 2.0 + (rel_pos / 0.15) * 13.0
        slope = 0.5 + (rel_pos / 0.15) * 2.5
        soil = 3
    elif rel_pos < 0.55:
        # Midlands Laterite Plateau (15 - 280m elev, 4 - 18 deg slope)
        p = (rel_pos - 0.15) / 0.40
        elev = 15.0 + (p * 265.0)
        slope = 4.0 + (p * 14.0)
        soil = 2
    else:
        # Highlands & Western Ghats Escarpments (350 - 2400m elev, 20 - 48 deg slope)
        p = (rel_pos - 0.55) / 0.45
        if is_idukki:
            elev = 750.0 + (p * 1650.0)
            slope = 28.0 + (p * 20.0)
        elif is_wayanad:
            elev = 700.0 + (p * 650.0)
            slope = 24.0 + (p * 16.0)
        elif is_silent_valley:
            elev = 600.0 + (p * 1100.0)
            slope = 26.0 + (p * 18.0)
        elif is_south_ghats:
            elev = 450.0 + (p * 1200.0)
            slope = 22.0 + (p * 18.0)
        else:
            elev = 350.0 + (p * 850.0)
            slope = 20.0 + (p * 16.0)
        soil = 1
        
    return round(elev, 1), round(slope, 1), soil


def fetch_nasa_elevation(lat, lng):
    try:
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lng}"
        res = requests.get(url, timeout=3).json()
        return float(res['results'][0]['elevation'])
    except Exception:
        return None


def fetch_reverse_geocoding(lat, lng):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lng}&limit=1&appid={OPENWEATHER_API_KEY}"
        res = requests.get(url, timeout=2).json()
        if res and len(res) > 0:
            name = res[0].get('name', '')
            state = res[0].get('state', '')
            return f"{name}, {state}" if state else name
    except Exception:
        pass
    return f"Sector ({lat:.3f}N, {lng:.3f}E)"


def generate_ollama_alert(location_name, risk_pct):
    system_prompt = (
        "You are an emergency SMS dispatcher. Output ONLY the plain text alert. "
        "Keep the entire message under 80 characters total."
    )
    user_prompt = f"Generate an ultra-short emergency SMS for {location_name} (Risk: {risk_pct:.0f}%)."
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "llama3.2:3b",
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {"num_predict": 45, "temperature": 0.1}
            },
            timeout=1.5
        )
        if response.status_code == 200:
            result = response.json().get('response', '').strip()
            result = result.replace('"', '').replace("'", "").replace('\n', ' ').strip()
            if len(result) > 120:
                result = result[:117] + "..."
            if result:
                return result
    except Exception:
        pass
    return f"EVACUATE: High landslide threat at {location_name}!"


# ==========================================================================
# 🔑 AUTHENTICATION & CITIZEN PROFILE ENDPOINTS
# ==========================================================================
@app.route('/api/auth/register', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
def register():
    import re
    import secrets
    try:
        data = request.json or {}
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        role = data.get("role", "Citizen").strip()
        lat = data.get("lat")
        lng = data.get("lng")
        district = data.get("district")

        # Optional coords parsing
        try:
            lat = float(lat) if lat is not None else None
            lng = float(lng) if lng is not None else None
        except (ValueError, TypeError):
            lat, lng = None, None

        # ── Name validation ─────────────────────────────────────────
        if not name:
            return jsonify({"success": False, "error": "Full name is required."}), 400
        if len(name) < 2:
            return jsonify({"success": False, "error": "Name must be at least 2 characters."}), 400
        if len(name) > 60:
            return jsonify({"success": False, "error": "Name must be under 60 characters."}), 400
        if not re.match(r"^[A-Za-z0-9\s\-\._'’]+$", name):
            return jsonify({"success": False, "error": "Name can only contain letters, numbers, spaces, hyphens, dots, or underscores."}), 400

        # ── Contact validation (Requires either phone OR email) ─────
        if not phone and not email:
            return jsonify({"success": False, "error": "Please provide either a mobile phone number or an email address."}), 400

        # Normalise & validate phone if provided
        if phone:
            phone_digits = re.sub(r"[\s\-]", "", phone)
            if phone_digits.startswith("+91"):
                phone_digits_only = phone_digits[3:]
            elif phone_digits.startswith("91") and len(phone_digits) == 12:
                phone_digits_only = phone_digits[2:]
            else:
                phone_digits_only = phone_digits.lstrip("+")
            if not re.match(r"^[6-9]\d{9}$", phone_digits_only):
                return jsonify({"success": False, "error": "Enter a valid 10-digit Indian mobile number (starts with 6-9)."}), 400
            phone = "+91" + phone_digits_only
        else:
            phone = None

        # Validate email if provided
        EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if email:
            if not re.match(EMAIL_REGEX, email):
                return jsonify({"success": False, "error": "Please enter a valid email address."}), 400
        else:
            email = None

        # ── Password validation ─────────────────────────────────────
        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400
        if len(password) < 8:
            return jsonify({"success": False, "error": "Password must be at least 8 characters long."}), 400
        if len(password) > 128:
            return jsonify({"success": False, "error": "Password is too long (max 128 characters)."}), 400
        if not re.search(r"[A-Za-z]", password):
            return jsonify({"success": False, "error": "Password must contain at least one letter."}), 400
        if not re.search(r"\d", password):
            return jsonify({"success": False, "error": "Password must contain at least one number."}), 400

        if role not in ("Citizen", "Volunteer"):
            role = "Citizen"

        existing_phone_user = get_user_by_phone(phone) if phone else None
        existing_email_user = get_user_by_email(email) if email else None

        # Check duplicate phone
        if existing_phone_user:
            if existing_phone_user.get("is_verified") or existing_phone_user.get("is_email_verified"):
                return jsonify({"success": False, "error": "A user with this phone number is already registered."}), 409
            if existing_email_user and existing_phone_user["id"] != existing_email_user["id"]:
                return jsonify({"success": False, "error": "A user with this phone number is already registered."}), 409

        # Check duplicate email
        if existing_email_user:
            if existing_email_user.get("is_email_verified") or existing_email_user.get("is_verified"):
                return jsonify({"success": False, "error": "An account with this email address is already registered."}), 409

        password_hash = hash_password(password)

        if email:
            # Email provided -> Dispatch 6-digit OTP for email verification
            otp_code = f"{secrets.randbelow(900000) + 100000}"

            # If user previously started registration but is still unverified, refresh their pending registration
            if existing_email_user and not existing_email_user.get("is_email_verified") and not existing_email_user.get("is_verified"):
                user_id = existing_email_user["id"]
                update_unverified_user(
                    user_id=user_id, name=name, phone=phone, password_hash=password_hash,
                    lat=lat, lng=lng, district=district, role=role, email_otp=otp_code
                )
                log_audit_action("USER_REGISTRATION_RESUMED", actor_id=user_id, target_id=user_id, details=f"Pending {role} registration refreshed for {email}. New OTP generated.")
            else:
                user_id = create_user(
                    name=name, phone=phone, email=email, password_hash=password_hash,
                    lat=lat, lng=lng, district=district, role=role,
                    is_verified=0, is_email_verified=0, email_otp=otp_code, credibility_score=50
                )
                log_audit_action("USER_REGISTERED_PENDING_VERIFY", actor_id=user_id, target_id=user_id, details=f"New {role} registered ({phone or 'No phone'}, {email}). OTP generated.")

            send_verification_email(email, name, otp_code)
            user_profile = get_user_by_id(user_id)
            token = generate_jwt_token(user_profile)

            return jsonify({
                "success": True,
                "message": f"Verification code sent to {email}",
                "email": email,
                "user_id": user_id,
                "dev_otp": otp_code,
                "token": token,
                "user": user_profile,
                "step": "verify_email"
            }), 201
        else:
            # Phone only provided -> Instant registration & verification
            user_id = create_user(
                name=name, phone=phone, email=None, password_hash=password_hash,
                lat=lat, lng=lng, district=district, role=role,
                is_verified=1, is_email_verified=0, credibility_score=50
            )
            log_audit_action("USER_REGISTERED_PHONE_ONLY", actor_id=user_id, target_id=user_id, details=f"New {role} registered with phone: {phone}.")
            user_profile = get_user_by_id(user_id)
            token = generate_jwt_token(user_profile)

            return jsonify({
                "success": True,
                "message": f"Welcome to TerraRisk AI, {name}!",
                "user_id": user_id,
                "token": token,
                "user": user_profile,
                "step": "complete"
            }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/verify-email', methods=['POST'])
@rate_limit(max_requests=15, window_seconds=60)
def verify_email():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        code = data.get("code", "").strip()

        if not email:
            return jsonify({"success": False, "error": "Email address is required."}), 400
        if not code or len(code) != 6 or not code.isdigit():
            return jsonify({"success": False, "error": "Please enter a valid 6-digit verification code."}), 400

        success, message, user_profile = verify_email_otp(email, code)
        if not success or not user_profile:
            return jsonify({"success": False, "error": message}), 400

        token = generate_jwt_token(user_profile)
        log_audit_action("USER_EMAIL_VERIFIED", actor_id=user_profile["id"], target_id=user_profile["id"], details=f"Email verified: {email}")

        return jsonify({
            "success": True,
            "message": "Email verified successfully! Welcome to TerraRisk AI.",
            "token": token,
            "user": user_profile
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/resend-code', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def resend_code():
    import secrets
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        if not email:
            return jsonify({"success": False, "error": "Email address is required."}), 400

        user = get_user_by_email(email)
        if not user:
            return jsonify({"success": False, "error": "No account found with this email address."}), 404

        if user.get("is_email_verified"):
            return jsonify({"success": True, "message": "Email is already verified. You can log in directly."}), 200

        new_otp = f"{secrets.randbelow(900000) + 100000}"
        set_email_otp(user["id"], new_otp, expires_in_minutes=10)
        send_verification_email(email, user.get("name", "Citizen"), new_otp)

        return jsonify({
            "success": True,
            "message": f"New verification code dispatched to {email}",
            "dev_otp": new_otp
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
def login():
    import re
    try:
        data = request.json or {}
        # Support identifier, phone, or email
        identifier = data.get("identifier") or data.get("phone") or data.get("email") or ""
        identifier = str(identifier).strip()
        password = data.get("password", "")

        if not identifier:
            return jsonify({"success": False, "error": "Mobile phone number or email address is required."}), 400
        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400

        user = get_user_by_identifier(identifier)
        if not user or not verify_password(password, user["password_hash"]):
            return jsonify({"success": False, "error": "Invalid credentials or user not found."}), 401

        # Check if email verification is still pending
        if user.get("email") and not user.get("is_email_verified") and not user.get("is_verified"):
            import secrets
            new_otp = f"{secrets.randbelow(900000) + 100000}"
            set_email_otp(user["id"], new_otp, expires_in_minutes=10)
            send_verification_email(user["email"], user.get("name", "Citizen"), new_otp)
            return jsonify({
                "success": False,
                "requires_verification": True,
                "email": user["email"],
                "dev_otp": new_otp,
                "error": "Your email address is not verified yet. A fresh 6-digit verification code has been dispatched to your email."
            }), 403

        user_profile = get_user_by_id(user["id"])
        token = generate_jwt_token(user_profile)
        log_audit_action("USER_LOGIN_SUCCESS", actor_id=user["id"], target_id=user["id"], details=f"{user['role']} logged in ({identifier})")

        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": user_profile
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user_profile(current_user):
    return jsonify({"success": True, "user": current_user})


@app.route('/api/user/check-safety', methods=['GET', 'POST'])
@token_required
def check_citizen_safety(current_user):
    try:
        data = request.json if request.is_json and request.json else {}
        lat = request.args.get('lat', type=float) or data.get('lat') or 11.5542
        lng = request.args.get('lng', type=float) or data.get('lng') or 76.1308

        lat = float(lat)
        lng = float(lng)

        raw_elev = fetch_nasa_elevation(lat, lng)
        elevation, slope, soil = resolve_kerala_topography(lat, lng, raw_elev)
        geo_name = fetch_reverse_geocoding(lat, lng)

        pressure_val = 1008.0
        live_humidity = 82.0
        temp_val = 24.0
        live_rainfall = 35.0

        try:
            owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={OPENWEATHER_API_KEY}&units=metric"
            w_res = requests.get(owm_url, timeout=2).json()
            if w_res.get('cod') == 200:
                pressure_val = float(w_res['main'].get('pressure', 1008.0))
                live_humidity = float(w_res['main'].get('humidity', 82.0))
                temp_val = float(w_res['main'].get('temp', 24.0))
                rain_dict = w_res.get('rain', {})
                live_rainfall = float(rain_dict.get('1h', rain_dict.get('3h', 12.0))) * 3.0
        except Exception:
            pass

        if rain_brain is not None:
            try:
                rain_input = pd.DataFrame([{'pressure': pressure_val, 'humidity': live_humidity, 'temp': temp_val}])
                pred_rain = float(rain_brain.predict(rain_input)[0])
                live_rainfall = max(0.0, pred_rain)
            except Exception:
                pass

        risk_pct = 5.0
        if slope < 8.0 and elevation < 150.0:
            risk_pct = 2.0
        elif ai_brain is not None:
            try:
                input_df = pd.DataFrame([{
                    'Slope_Angle': slope, 'Elevation': elevation, 'Soil_Type': soil,
                    'Rainfall_72h': live_rainfall, 'Soil_Saturation': live_humidity
                }])
                if hasattr(ai_brain, 'predict_proba'):
                    risk_pct = float(ai_brain.predict_proba(input_df)[0][1] * 100.0)
                else:
                    risk_pct = float(ai_brain.predict(input_df)[0])
            except Exception:
                risk_pct = min(99.0, (slope * 1.5) + (live_rainfall * 0.15))
        else:
            risk_pct = min(99.0, (slope * 1.5) + (live_rainfall * 0.15))

        risk_pct = max(0.0, min(100.0, risk_pct))

        if risk_pct >= 70.0 or live_rainfall >= 160.0:
            status = "Critical"
            status_color = "#FF453A"
            advisory = f"CRITICAL THREAT: High slope failure probability at {geo_name}. Evacuate immediately."
        elif risk_pct >= 35.0 or live_rainfall >= 60.0:
            status = "Advisory"
            status_color = "#FF9F0A"
            advisory = f"WEATHER ADVISORY: Elevated soil saturation detected in {geo_name}. Monitor tension cracks."
        else:
            status = "Safe"
            status_color = "#30D158"
            advisory = f"ALL CLEAR: Nominal geological and atmospheric conditions verified in {geo_name}."

        nearby_shelters = get_nearby_shelters(lat, lng, radius_km=30.0)
        nearest_shelter = nearby_shelters[0] if nearby_shelters else None
        nearby_incidents = get_nearby_incidents(lat, lng, radius_km=15.0, status="verified")

        return jsonify({
            "success": True,
            "status": status,
            "status_color": status_color,
            "risk_percentage": round(risk_pct, 1),
            "live_rainfall": round(live_rainfall, 1),
            "live_humidity": round(live_humidity, 1),
            "elevation": round(elevation, 1),
            "slope": round(slope, 1),
            "location_name": geo_name,
            "advisory": advisory,
            "nearest_shelter": nearest_shelter,
            "nearby_incidents_count": len(nearby_incidents),
            "nearby_incidents": nearby_incidents[:3],
            "checked_at": datetime.datetime.utcnow().isoformat() + "Z"
        })
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


# ==========================================================================
# 📡 CORE ANALYTICS ENDPOINTS (Predict, Hotspots, Forecast)
# ==========================================================================
@app.route('/api/hotspots', methods=['GET'])
def get_hotspots():
    return jsonify(HOTSPOTS)


@app.route('/api/predict', methods=['POST'])
def predict_risk():
    try:
        data = request.json or {}
        lat = float(data.get('lat', 11.6920))
        lng = float(data.get('lng', 76.1450))
        true_elev = fetch_nasa_elevation(lat, lng)
        auto_elev, auto_slope, auto_soil = resolve_kerala_topography(lat, lng, true_elev)

        elevation = true_elev if true_elev is not None else float(data.get('elevation', auto_elev))
        slope = float(data['slope']) if 'slope' in data else auto_slope
        soil = int(data['soil']) if 'soil' in data else auto_soil
        sim_mode = data.get('sim_mode', False)
        manual_rainfall = float(data.get('manual_rainfall', 150))
        manual_saturation = float(data.get('manual_saturation', 60))

        geo_name = fetch_reverse_geocoding(lat, lng)

        pressure_val = 1008.0
        live_humidity = 85.0
        temp_val = 24.0
        live_rainfall = 45.0

        try:
            owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={OPENWEATHER_API_KEY}&units=metric"
            w_res = requests.get(owm_url, timeout=2).json()
            if w_res.get('cod') == 200:
                pressure_val = float(w_res['main'].get('pressure', 1008.0))
                live_humidity = float(w_res['main'].get('humidity', 85.0))
                temp_val = float(w_res['main'].get('temp', 24.0))
                rain_dict = w_res.get('rain', {})
                live_rainfall = float(rain_dict.get('1h', rain_dict.get('3h', 15.0))) * 3.0
        except Exception:
            pass

        if not sim_mode and rain_brain is not None:
            try:
                rain_input = pd.DataFrame([{'pressure': pressure_val, 'humidity': live_humidity, 'temp': temp_val}])
                predicted_rain = float(rain_brain.predict(rain_input)[0])
                live_rainfall = max(0.0, predicted_rain)
            except Exception:
                pass

        final_rainfall = manual_rainfall if sim_mode else live_rainfall
        final_humidity = manual_saturation if sim_mode else live_humidity

        if slope < 8.0 and elevation < 150.0:
            risk_pct = 2.5
        elif ai_brain is not None:
            try:
                input_df = pd.DataFrame([{
                    'Slope_Angle': slope, 'Elevation': elevation, 'Soil_Type': soil,
                    'Rainfall_72h': final_rainfall, 'Soil_Saturation': final_humidity
                }])
                if hasattr(ai_brain, 'predict_proba'):
                    prob = ai_brain.predict_proba(input_df)[0][1]
                    risk_pct = float(prob * 100.0)
                else:
                    pred = ai_brain.predict(input_df)[0]
                    risk_pct = float(pred)
            except Exception:
                risk_pct = min(99.0, (slope * 1.5) + (final_rainfall * 0.15))
        else:
            risk_pct = min(99.0, (slope * 1.5) + (final_rainfall * 0.15))

        risk_pct = max(0.0, min(100.0, risk_pct))

        alert_text = ""
        if risk_pct >= 80.0:
            alert_text = generate_ollama_alert(geo_name, risk_pct)

        return jsonify({
            "risk_percentage": round(risk_pct, 1),
            "live_rainfall": round(final_rainfall, 1),
            "live_humidity": round(final_humidity, 1),
            "alert_text": alert_text,
            "geo_name": geo_name,
            "true_elevation": round(elevation, 1)
        })
    except Exception as outer_err:
        return jsonify({"error": str(outer_err)}), 500


@app.route('/api/forecast', methods=['POST'])
def get_forecast():
    try:
        data = request.json or {}
        lat = float(data.get('lat', 11.6920))
        lng = float(data.get('lng', 76.1450))

        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=3).json()

        if res.get('cod') != '200':
            return jsonify({"success": False, "error": "Forecast fetch error"}), 400

        daily_list = []
        raw_list = res.get('list', [])

        for item in raw_list[::8][:3]:
            dt = datetime.datetime.fromtimestamp(item['dt'])
            cond_main = item['weather'][0]['main'].lower()
            cond = 'clear'
            if 'rain' in cond_main or 'drizzle' in cond_main: cond = 'rain'
            elif 'thunderstorm' in cond_main: cond = 'thunderstorm'
            elif 'cloud' in cond_main: cond = 'clouds'

            daily_list.append({
                "day": dt.strftime('%a'),
                "temp": round(item['main']['temp'], 1),
                "desc": item['weather'][0]['description'].title(),
                "condition": cond,
                "humidity": item['main']['humidity']
            })

        return jsonify({"success": True, "forecast": daily_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/forecast/temporal-risk', methods=['POST'])
def get_temporal_risk_forecast():
    try:
        data = request.json or {}
        lat = float(data.get('lat', 11.5542))
        lng = float(data.get('lng', 76.1308))
        auto_elev, auto_slope, auto_soil = resolve_kerala_topography(lat, lng)
        slope = float(data['slope']) if 'slope' in data else auto_slope
        elevation = float(data['elevation']) if 'elevation' in data else auto_elev
        soil = int(data['soil']) if 'soil' in data else auto_soil
        
        base_rainfall = float(data.get('current_rainfall', 40.0))
        base_saturation = float(data.get('current_saturation', 75.0))
        rain_trend = float(data.get('rain_trend', 1.8))

        intervals = [
            {"hour": 0, "label": "Now (0h)", "added_rain": 0.0},
            {"hour": 6, "label": "+6 Hours", "added_rain": 25.0 * rain_trend},
            {"hour": 12, "label": "+12 Hours", "added_rain": 55.0 * rain_trend},
            {"hour": 24, "label": "+24 Hours", "added_rain": 115.0 * rain_trend},
            {"hour": 36, "label": "+36 Hours", "added_rain": 180.0 * rain_trend},
            {"hour": 48, "label": "+48 Hours", "added_rain": 250.0 * rain_trend}
        ]

        timeline = []
        is_guard_active = slope < 8.0 and elevation < 150.0

        for it in intervals:
            cum_rain = base_rainfall + it["added_rain"]
            sim_saturation = min(99.0, base_saturation + (it["added_rain"] * 0.12))
            
            if is_guard_active:
                risk_pct = 2.0
            elif ai_brain is not None:
                try:
                    df = pd.DataFrame([{
                        'Slope_Angle': slope, 'Elevation': elevation, 'Soil_Type': soil,
                        'Rainfall_72h': cum_rain, 'Soil_Saturation': sim_saturation
                    }])
                    if hasattr(ai_brain, 'predict_proba'):
                        risk_pct = float(ai_brain.predict_proba(df)[0][1] * 100.0)
                    else:
                        risk_pct = float(ai_brain.predict(df)[0])
                except Exception:
                    risk_pct = min(99.0, (slope * 1.5) + (cum_rain * 0.18))
            else:
                risk_pct = min(99.0, (slope * 1.5) + (cum_rain * 0.18))

            risk_pct = max(0.0, min(100.0, risk_pct))
            level = "Critical Threat" if risk_pct >= 80.0 else "Active Warning" if risk_pct >= 45.0 else "Nominal Stability"
            level_color = "#EF4444" if risk_pct >= 80.0 else "#F59E0B" if risk_pct >= 45.0 else "#30D158"

            timeline.append({
                "hour": it["hour"],
                "label": it["label"],
                "cumulative_rainfall": round(cum_rain, 1),
                "added_rainfall": round(it["added_rain"], 1),
                "soil_saturation": round(sim_saturation, 1),
                "risk_percentage": round(risk_pct, 1),
                "level": level,
                "level_color": level_color
            })

        return jsonify({"success": True, "lat": lat, "lng": lng, "slope": slope, "elevation": elevation, "timeline": timeline})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 👁️ COMPUTER VISION HAZARD TRIAGE ENDPOINTS
# ==========================================================================
@app.route('/api/vision/analyze', methods=['POST'])
@rate_limit(max_requests=20, window_seconds=60)
def analyze_vision_image():
    """Analyze a photo for geological hazard characteristics and spam probability."""
    try:
        data = request.json or {}
        image_input = data.get("image") or data.get("image_url")
        hazard_type = data.get("hazard_type", "slope_movement")
        
        cv_result = analyze_hazard_image(image_input, reported_hazard=hazard_type)
        return jsonify({"success": True, "analysis": cv_result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 🚨 CITIZEN INCIDENT REPORTING & AUTO-CLUSTERING
# ==========================================================================
@app.route('/api/incidents/report', methods=['POST'])
@token_required
def report_incident(current_user):
    try:
        data = request.json or {}
        hazard_type = data.get("hazard_type", "mud_crack")
        lat = data.get("lat")
        lng = data.get("lng")
        description = data.get("description", "").strip()
        severity = data.get("severity", 3)
        image_url = data.get("image_url") or data.get("image")

        valid_hazards = ('mud_crack', 'stream_overflow', 'rockfall', 'blocked_road', 'slope_movement')
        if hazard_type not in valid_hazards:
            return jsonify({"success": False, "error": f"Invalid hazard_type. Must be one of: {', '.join(valid_hazards)}"}), 400

        if lat is None or lng is None:
            return jsonify({"success": False, "error": "Latitude and longitude coordinates are required"}), 400

        lat = float(lat)
        lng = float(lng)
        severity = max(1, min(5, int(severity)))

        # 1. Run 3-Tier Computer Vision Hazard Brain if image is attached
        cv_analysis = None
        ai_conf = None
        ai_haz = None
        ai_sev = None
        ai_sum = None
        is_spam_flag = 0

        if image_url:
            cv_analysis = analyze_hazard_image(image_url, reported_hazard=hazard_type)
            ai_conf = cv_analysis.get("confidence_score")
            ai_haz = cv_analysis.get("detected_hazard")
            ai_sev = cv_analysis.get("suggested_severity")
            ai_sum = cv_analysis.get("ai_summary")
            is_spam_flag = 1 if cv_analysis.get("is_spam") else 0

        # 2. Spatial Auto-Clustering (500m / 2h)
        cluster_id = find_nearby_pending_cluster(lat=lat, lng=lng, radius_km=0.5, hours_window=2.0)
        is_clustered = cluster_id is not None
        if not cluster_id:
            import secrets
            cluster_id = f"clust_{int(datetime.datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"

        # 3. Save report with AI metadata
        incident_id = create_incident_report(
            user_id=current_user["id"],
            hazard_type=hazard_type,
            lat=lat,
            lng=lng,
            description=description,
            severity=severity,
            image_url=image_url if (image_url and len(image_url) < 300) else None,
            cluster_id=cluster_id,
            status="pending",
            ai_confidence=ai_conf,
            ai_hazard_type=ai_haz,
            ai_severity=ai_sev,
            ai_summary=ai_sum,
            is_flagged_spam=is_spam_flag
        )

        # 4. Check for auto-verification consensus threshold (>= 5 reports in area)
        is_auto_verified, report_consensus_count = check_and_autoverify_cluster(cluster_id, threshold=5)

        log_audit_action(
            "INCIDENT_REPORTED",
            actor_id=current_user["id"],
            target_id=incident_id,
            details=f"Hazard: {hazard_type} (Sev: {severity}) | AI Conf: {ai_conf} | Cluster: {cluster_id} | AutoVerified: {is_auto_verified} ({report_consensus_count} reports)"
        )

        msg = "Hazard report submitted and analyzed by Computer Vision Brain."
        if is_auto_verified:
            msg = f"Hazard report submitted. Cluster reached {report_consensus_count} community reports and has been AUTO-VERIFIED on the map!"

        return jsonify({
            "success": True,
            "message": msg,
            "incident_id": incident_id,
            "cluster_id": cluster_id,
            "is_clustered": is_clustered,
            "is_auto_verified": is_auto_verified,
            "consensus_count": report_consensus_count,
            "ai_analysis": cv_analysis
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/incidents/active', methods=['GET'])
def get_active_incidents():
    try:
        clusters = get_active_incident_clusters()
        return jsonify({"success": True, "count": len(clusters), "incidents": clusters})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 🛡️ AUTHORITY TRIAGE DASHBOARD & CREDIBILITY ENGINE
# ==========================================================================
@app.route('/api/authority/pending-clusters', methods=['GET'])
@app.route('/api/authority/clusters', methods=['GET'])
@token_required
@authority_required
def get_authority_pending_clusters(current_user):
    try:
        status_param = request.args.get("status", "all").strip().lower()
        clusters = get_pending_incident_clusters(status_filter=status_param)
        return jsonify({"success": True, "count": len(clusters), "clusters": clusters})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/authority/metrics', methods=['GET'])
@token_required
@authority_required
def get_triage_metrics(current_user):
    try:
        metrics = get_authority_metrics()
        return jsonify({"success": True, "metrics": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/incidents/verify', methods=['POST'])
@token_required
@authority_required
def verify_incident(current_user):
    try:
        data = request.json or {}
        cluster_id = data.get("cluster_id") or data.get("incident_id")
        if not cluster_id:
            return jsonify({"success": False, "error": "cluster_id parameter is required"}), 400
            
        result = verify_incident_cluster(cluster_id=str(cluster_id), verified_by_user_id=current_user["id"])
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/incidents/reject', methods=['POST'])
@token_required
@authority_required
def reject_incident(current_user):
    try:
        data = request.json or {}
        cluster_id = data.get("cluster_id") or data.get("incident_id")
        reason = data.get("reason", "Spam / False Alarm").strip()
        if not cluster_id:
            return jsonify({"success": False, "error": "cluster_id parameter is required"}), 400
            
        result = reject_incident_cluster(cluster_id=str(cluster_id), rejected_by_user_id=current_user["id"], reason=reason)
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/incidents/resolve', methods=['POST'])
@token_required
@authority_required
def resolve_incident(current_user):
    """Mark an active hazard cluster as resolved/cleared once field teams mitigate it."""
    try:
        data = request.json or {}
        cluster_id = data.get("cluster_id") or data.get("incident_id")
        notes = data.get("notes", "Site Cleared / Hazard Mitigated").strip()
        if not cluster_id:
            return jsonify({"success": False, "error": "cluster_id parameter is required"}), 400
            
        result = resolve_incident_cluster(cluster_id=str(cluster_id), resolved_by_user_id=current_user["id"], notes=notes)
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/authority/users/verify', methods=['POST'])
@token_required
@authority_required
def verify_user_account(current_user):
    """Directly set user verification status (Admin Verification)."""
    try:
        data = request.json or {}
        user_id = data.get("user_id")
        is_verified = bool(data.get("is_verified", True))
        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400
            
        success = set_user_verification(int(user_id), is_verified)
        if not success:
            return jsonify({"success": False, "error": "User not found or update failed."}), 404
            
        log_audit_action(
            "USER_VERIFIED" if is_verified else "USER_UNVERIFIED",
            actor_id=current_user["id"],
            target_id=int(user_id),
            details=f"User {user_id} verification status set to {is_verified} by Admin {current_user['name']}"
        )
        return jsonify({
            "success": True,
            "message": f"User verification updated to {'Verified' if is_verified else 'Unverified'}.",
            "user_id": int(user_id),
            "is_verified": is_verified
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 📢 MULTI-CHANNEL ZERO-COST BROADCASTING & CAP v1.2
# ==========================================================================
@app.route('/api/alerts/preview', methods=['POST'])
@token_required
@authority_required
def preview_geofenced_alert(current_user):
    try:
        data = request.json or {}
        lat = float(data.get("lat", 11.5542))
        lng = float(data.get("lng", 76.1308))
        radius_km = float(data.get("radius_km", 5.0))
        hazard_type = data.get("hazard_type", "slope_movement")
        severity = int(data.get("severity", 3))
        
        geo_name = fetch_reverse_geocoding(lat, lng) or f"Sector ({lat:.3f}N, {lng:.3f}E)"
        synthesis = synthesize_bilingual_alert(hazard_type=hazard_type, location_name=geo_name, severity=severity, radius_km=radius_km)
        target_citizens = get_users_in_radius(lat=lat, lng=lng, radius_km=radius_km)
        wa_link = generate_whatsapp_broadcast_link(synthesis["alert_en"], synthesis["alert_ml"], lat, lng, radius_km, hazard_type)
        
        return jsonify({
            "success": True,
            "hazard_type": hazard_type,
            "location_name": geo_name,
            "radius_km": radius_km,
            "target_citizens_count": len(target_citizens),
            "alert_en": synthesis["alert_en"],
            "alert_ml": synthesis["alert_ml"],
            "whatsapp_share_url": wa_link,
            "synthesis_source": synthesis["source"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/alerts/broadcast', methods=['POST'])
@token_required
@authority_required
def broadcast_geofenced_alert(current_user):
    try:
        data = request.json or {}
        lat = float(data.get("lat", 11.5542))
        lng = float(data.get("lng", 76.1308))
        radius_km = float(data.get("radius_km", 5.0))
        hazard_type = data.get("hazard_type", "slope_movement")
        alert_en = data.get("alert_en", "").strip()
        alert_ml = data.get("alert_ml", "").strip()
        
        if not alert_en or not alert_ml:
            geo_name = fetch_reverse_geocoding(lat, lng)
            synthesis = synthesize_bilingual_alert(hazard_type, geo_name, severity=4, radius_km=radius_km)
            alert_en = alert_en or synthesis["alert_en"]
            alert_ml = alert_ml or synthesis["alert_ml"]
            
        result = dispatch_multi_channel_alert(
            lat=lat, lng=lng, radius_km=radius_km,
            alert_en=alert_en, alert_ml=alert_ml, hazard_type=hazard_type,
            sender_name=f"{current_user.get('name', 'Authority')} ({current_user.get('role', 'Admin')})"
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/broadcast', methods=['POST'])
@app.route('/api/sms/blast', methods=['POST'])
@token_required
@authority_required
@rate_limit(max_requests=10, window_seconds=60)
def direct_sms_broadcast_endpoint(current_user):
    """Live Twilio Cellular SMS Gateway Dispatcher with automatic zero-cost simulation fallback."""
    try:
        data = request.json or {}
        alert_text = data.get("alert_text") or "EVACUATE: High Landslide Threat detected by TerraRisk AI."
        target_phone = data.get("phone") or YOUR_PERSONAL_MOBILE or "+919999900000"

        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=alert_text,
                    from_=TWILIO_PHONE_NUMBER,
                    to=target_phone
                )
                print(f"[OK] Live Twilio SMS sent to {target_phone}! SID: {message.sid}")
                log_audit_action("TWILIO_SMS_DISPATCHED", actor_id=current_user.get("id"), details=f"Sent to {target_phone} | SID: {message.sid} by {current_user.get('name')}")
                return jsonify({
                    "success": True,
                    "message": "SMS Broadcast Dispatched via Twilio",
                    "sid": message.sid,
                    "phone": target_phone,
                    "status": "delivered"
                }), 200
            except Exception as tw_err:
                print(f"[WARNING] Twilio API Gateway note: {tw_err}")
                sim_sid = f"sim_tw_{int(datetime.datetime.utcnow().timestamp())}"
                return jsonify({
                    "success": True,
                    "message": f"Twilio SMS Simulated: {str(tw_err)[:60]}",
                    "sid": sim_sid,
                    "phone": target_phone,
                    "status": "simulated"
                }), 200
        else:
            sim_sid = f"sim_sms_{int(datetime.datetime.utcnow().timestamp())}"
            return jsonify({
                "success": True,
                "message": "SMS Broadcast Simulated (No Twilio Credentials in .env)",
                "sid": sim_sid,
                "phone": target_phone,
                "status": "simulated"
            }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/alerts/active-broadcasts', methods=['GET'])
def get_active_emergency_broadcasts():
    try:
        broadcasts = get_active_broadcasts(hours_window=24.0)
        return jsonify({"success": True, "count": len(broadcasts), "broadcasts": broadcasts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/alerts/cap.xml', methods=['GET'])
def get_cap_xml_feed():
    try:
        incidents = get_active_incident_clusters()
        broadcasts = get_active_broadcasts(hours_window=24.0)
        xml_content = generate_cap_xml(incidents, broadcasts)
        return Response(xml_content, mimetype='application/xml')
    except Exception as e:
        return Response(f"<error>{str(e)}</error>", mimetype='application/xml', status=500)


@app.route('/api/alerts/cap.json', methods=['GET'])
def get_cap_json_feed():
    try:
        incidents = get_active_incident_clusters()
        broadcasts = get_active_broadcasts(hours_window=24.0)
        return jsonify(generate_cap_json(incidents, broadcasts))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# ⛺ RELIEF SHELTER & INVENTORY MANAGEMENT (CRUD)
# ==========================================================================
@app.route('/api/shelters', methods=['GET'])
def get_shelters():
    try:
        lat = request.args.get('lat', type=float) or 11.5361
        lng = request.args.get('lng', type=float) or 76.1667
        radius = request.args.get('radius_km', default=None, type=float)
        district = request.args.get('district', default=None, type=str)
        status = request.args.get('status', default=None, type=str)
        
        shelters = get_nearby_shelters(lat=lat, lng=lng, radius_km=radius, district=district, status=status)
        return jsonify({"success": True, "count": len(shelters), "shelters": shelters})
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


@app.route('/api/shelters/<int:shelter_id>', methods=['GET'])
def get_single_shelter(shelter_id):
    try:
        shelter = get_shelter_by_id(shelter_id)
        if not shelter:
            return jsonify({"success": False, "error": "Relief shelter not found"}), 404
        return jsonify({"success": True, "shelter": shelter})
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


@app.route('/api/shelters/create', methods=['POST'])
@token_required
@authority_required
def create_new_shelter(current_user):
    try:
        data = request.json or {}
        name = data.get("name", "").strip()
        lat = data.get("lat")
        lng = data.get("lng")
        capacity = data.get("capacity", 100)
        contact_number = data.get("contact_number", "").strip()
        district = data.get("district", "Wayanad").strip()
        in_charge_name = data.get("in_charge_name", "").strip()
        in_charge_phone = data.get("in_charge_phone", "").strip()
        supplies = data.get("supplies", {})
        amenities = data.get("amenities", {})
        status = data.get("status", "active").strip()

        if not name or lat is None or lng is None or not contact_number:
            return jsonify({"success": False, "error": "Name, coordinates (lat, lng), and contact number are required"}), 400

        shelter_id = create_relief_shelter(
            name=name, lat=float(lat), lng=float(lng), capacity=int(capacity),
            contact_number=contact_number, district=district,
            in_charge_name=in_charge_name, in_charge_phone=in_charge_phone,
            supplies_dict=supplies, amenities_dict=amenities, status=status
        )

        log_audit_action("SHELTER_CREATED", actor_id=current_user["id"], target_id=shelter_id, details=f"New shelter '{name}' (Capacity: {capacity}) created by {current_user['name']}")
        created_shelter = get_shelter_by_id(shelter_id)

        return jsonify({"success": True, "message": "Relief shelter created successfully", "shelter": created_shelter}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shelters/<int:shelter_id>', methods=['PUT'])
@token_required
@authority_required
def modify_shelter(current_user, shelter_id):
    try:
        data = request.json or {}
        success = update_relief_shelter(
            shelter_id=shelter_id,
            name=data.get("name"),
            lat=data.get("lat"),
            lng=data.get("lng"),
            capacity=data.get("capacity"),
            contact_number=data.get("contact_number"),
            district=data.get("district"),
            in_charge_name=data.get("in_charge_name"),
            in_charge_phone=data.get("in_charge_phone"),
            status=data.get("status"),
            supplies_dict=data.get("supplies"),
            amenities_dict=data.get("amenities")
        )
        if not success:
            return jsonify({"success": False, "error": "Failed to update shelter or no fields provided"}), 400

        log_audit_action("SHELTER_UPDATED", actor_id=current_user["id"], target_id=shelter_id, details=f"Shelter ID {shelter_id} updated by {current_user['name']}")
        updated = get_shelter_by_id(shelter_id)
        return jsonify({"success": True, "message": "Shelter updated successfully", "shelter": updated}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shelters/<int:shelter_id>', methods=['DELETE'])
@token_required
@authority_required
def remove_shelter(current_user, shelter_id):
    try:
        success = delete_relief_shelter(shelter_id)
        if not success:
            return jsonify({"success": False, "error": "Shelter not found or could not be deleted"}), 404

        log_audit_action("SHELTER_DELETED", actor_id=current_user["id"], target_id=shelter_id, details=f"Shelter ID {shelter_id} deleted by {current_user['name']}")
        return jsonify({"success": True, "message": f"Relief shelter {shelter_id} deleted successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shelters/<int:shelter_id>/supplies', methods=['POST'])
@token_required
@authority_required
def modify_shelter_supplies_endpoint(current_user, shelter_id):
    try:
        data = request.json or {}
        supplies_dict = data.get("supplies") or data
        result = update_shelter_supplies(shelter_id, supplies_dict)
        if not result.get("success"):
            return jsonify(result), 400

        log_audit_action("SHELTER_SUPPLIES_UPDATED", actor_id=current_user["id"], target_id=shelter_id, details=f"Supplies updated for shelter {shelter_id}")
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shelters/update-occupancy', methods=['POST'])
@token_required
@authority_required
def modify_shelter_occupancy(current_user):
    try:
        data = request.json or {}
        shelter_id = data.get("shelter_id")
        occupied = data.get("occupied")
        if shelter_id is None or occupied is None:
            return jsonify({"success": False, "error": "shelter_id and occupied fields are required"}), 400
            
        result = update_shelter_occupancy(shelter_id=int(shelter_id), occupied=int(occupied))
        if not result.get("success"):
            return jsonify(result), 400
            
        log_audit_action("SHELTER_OCCUPANCY_UPDATED", actor_id=current_user["id"], target_id=shelter_id, details=f"Shelter {shelter_id} occupancy set to {result['occupied']}/{result['capacity']}")
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 📋 MISSING PERSONS & RESCUE REQUEST REGISTRY
# ==========================================================================
@app.route('/api/missing-persons', methods=['GET'])
def list_missing_persons():
    try:
        status = request.args.get('status')
        query = request.args.get('query')
        limit = request.args.get('limit', default=100, type=int)
        persons = get_missing_persons(status=status, query=query, limit=limit)
        return jsonify({"success": True, "count": len(persons), "missing_persons": persons})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/missing-persons/report', methods=['POST'])
def submit_missing_person_report():
    try:
        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "error": "Name of missing individual is required"}), 400

        auth_header = request.headers.get("Authorization", "")
        reported_by_uid = None
        if auth_header.startswith("Bearer "):
            payload = verify_jwt_token(auth_header.split(" ", 1)[1].strip())
            if payload: reported_by_uid = payload.get("user_id")

        person_id = create_missing_person(
            name=name,
            age=data.get("age"),
            gender=data.get("gender"),
            last_known_location=data.get("last_known_location", "").strip(),
            lat=data.get("lat"),
            lng=data.get("lng"),
            contact_phone=data.get("contact_phone", "").strip(),
            photo_url=data.get("photo_url"),
            medical_needs=data.get("medical_needs", "").strip(),
            reported_by_user_id=reported_by_uid
        )
        return jsonify({"success": True, "message": "Missing person report registered in SOS board", "person_id": person_id}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/missing-persons/<int:person_id>/update-status', methods=['POST'])
@token_required
@authority_required
def change_missing_person_status(current_user, person_id):
    try:
        data = request.json or {}
        status = data.get("status", "located_safe")
        shelter_id = data.get("located_at_shelter_id")
        
        success = update_missing_person_status(person_id=person_id, status=status, located_at_shelter_id=shelter_id)
        if not success:
            return jsonify({"success": False, "error": "Failed to update missing person status"}), 400
            
        log_audit_action("MISSING_PERSON_STATUS_UPDATED", actor_id=current_user["id"], target_id=person_id, details=f"Status set to '{status}' (Shelter: {shelter_id})")
        return jsonify({"success": True, "message": f"Status updated to '{status}'"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



# ==========================================================================
# 🦺 FIELD VOLUNTEER MISSION DISPATCH
# ==========================================================================
@app.route('/api/authority/missions', methods=['GET'])
@token_required
@authority_required
def get_missions_endpoint(current_user):
    try:
        status = request.args.get('status')
        missions = get_volunteer_missions(status=status)
        return jsonify({"success": True, "count": len(missions), "missions": missions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/authority/missions/assign', methods=['POST'])
@token_required
@authority_required
def assign_mission_endpoint(current_user):
    try:
        data = request.json or {}
        cluster_id = data.get("cluster_id")
        volunteer_id = data.get("volunteer_id")
        notes = data.get("notes", "Field verification mission dispatched.").strip()
        
        if not cluster_id:
            return jsonify({"success": False, "error": "cluster_id is required"}), 400
            
        mission_id = create_volunteer_mission(
            cluster_id=str(cluster_id),
            volunteer_id=int(volunteer_id) if volunteer_id else None,
            assigned_by=current_user["id"],
            notes=notes
        )
        log_audit_action("VOLUNTEER_MISSION_ASSIGNED", actor_id=current_user["id"], target_id=mission_id, details=f"Mission {mission_id} assigned to volunteer {volunteer_id} for cluster {cluster_id}")
        return jsonify({"success": True, "message": "Volunteer mission dispatched successfully", "mission_id": mission_id}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/volunteer/missions/<int:mission_id>/update-status', methods=['POST'])
@token_required
def update_mission_status_endpoint(current_user, mission_id):
    try:
        data = request.json or {}
        status = data.get("status", "verified")
        notes = data.get("notes")
        
        success = update_volunteer_mission_status(mission_id=mission_id, status=status, notes=notes)
        if not success:
            return jsonify({"success": False, "error": "Mission not found or update failed"}), 400
            
        log_audit_action("MISSION_STATUS_UPDATED", actor_id=current_user["id"], target_id=mission_id, details=f"Mission {mission_id} status updated to '{status}'")
        return jsonify({"success": True, "message": f"Mission status updated to '{status}'"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 🧭 SAFE EVACUATION ROUTE PLANNER
# ==========================================================================
@app.route('/api/routes/evacuate', methods=['POST'])
def plan_evacuation_route():
    try:
        data = request.json or {}
        start_lat = data.get("start_lat") or 11.5542
        start_lng = data.get("start_lng") or 76.1308
        dest_shelter_id = data.get("destination_shelter_id")
        
        start_lat = float(start_lat)
        start_lng = float(start_lng)
        if dest_shelter_id is not None:
            dest_shelter_id = int(dest_shelter_id)
            
        route_plan = calculate_evacuation_route(
            start_lat=start_lat,
            start_lng=start_lng,
            destination_shelter_id=dest_shelter_id
        )
        return jsonify(route_plan), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# 📄 SITUATION REPORT (SITREP) EXPORTER
# ==========================================================================
@app.route('/api/authority/export-sitrep', methods=['GET', 'POST'])
@token_required
@authority_required
def export_situation_report(current_user):
    try:
        report_format = request.args.get('format', default='pdf').lower()
        district = request.args.get('district', default=None)
        officer_title = f"{current_user.get('name', 'SEOC Officer')} ({current_user.get('role', 'Authority_Admin').replace('_', ' ')})"
        
        if report_format == 'json':
            sitrep_json = generate_sitrep_data(district=district)
            return jsonify({"success": True, "sitrep": sitrep_json}), 200
            
        pdf_bytes = generate_sitrep_pdf(district=district, author_name=officer_title)
        timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        district_suffix = f"_{district}" if district else "_Statewide"
        filename = f"KSDMA_SitRep{district_suffix}_{timestamp_str}.pdf"
        
        log_audit_action("SITREP_EXPORTED", actor_id=current_user["id"], details=f"Official KSDMA SitRep PDF exported ({district or 'Statewide'})")
        
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def get_system_health():
    try:
        db_info = get_database_info()
        is_healthy = db_info.get("connected", False)
        return jsonify({
            "status": "healthy" if is_healthy else "degraded",
            "models": {
                "classifier_loaded": ai_brain is not None,
                "regressor_loaded": rain_brain is not None,
                "vision_engine": "active"
            },
            "database": db_info
        }), (200 if is_healthy else 500)
    except Exception as err:
        return jsonify({"status": "degraded", "error": str(err)}), 500


# ==========================================================================
# 🚀 SERVER LAUNCH
# ==========================================================================
if __name__ == '__main__':
    print("\n[INFO] Launching TerraRisk AI Complete Intelligence Core...")
    app.run(host='0.0.0.0', port=5000, debug=True)