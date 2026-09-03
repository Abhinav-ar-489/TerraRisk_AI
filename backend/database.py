"""
TerraRisk AI - Database & Credibility Architecture
SQLite database engine managing user authentication, credibility scoring,
crowdsourced incident reports, relief shelter lifecycle & inventory,
missing persons registry, family safety circles, volunteer task dispatches,
and tamper-evident audit logging.
"""

import os
import sys
import math
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from dotenv import load_dotenv

# Supabase / PostgreSQL cloud connection support
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# Force UTF-8 encoding on Windows console streams if available
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Determine canonical path to backend/data/disaster_platform.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "disaster_platform.db")

# Automatically load environment variables from backend/.env
load_dotenv(os.path.join(BASE_DIR, ".env"))


# ==============================================================================
# PASSWORD SECURITY UTILITIES (PBKDF2-HMAC-SHA256)
# ==============================================================================
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Generate a secure salted PBKDF2-HMAC-SHA256 hash."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against stored salted hash."""
    try:
        salt, key = hashed_password.split('$', 1)
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(key, new_key)
    except Exception:
        return False


# ==============================================================================
# POSTGRESQL / SUPABASE SQL ADAPTER & WRAPPERS
# ==============================================================================
def is_postgres_configured(db_path: Optional[str] = None) -> bool:
    """Return True if PostgreSQL / Supabase connection is active and requested."""
    if db_path is not None:
        # Explicit path (like test .db) forces SQLite
        return False
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    return bool(url and (url.startswith("postgresql://") or url.startswith("postgres://")))


def adapt_sql_for_pg(sql: str) -> str:
    """
    Translates SQLite parameterized SQL query to PostgreSQL format:
    1. Replaces '?' placeholders with '%s' (preserving '?' inside string literals).
    """
    if not sql or '?' not in sql:
        return sql

    out = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]
        if c == "'" and not in_double_quote:
            if in_single_quote and i + 1 < n and sql[i + 1] == "'":
                out.append("''")
                i += 2
                continue
            in_single_quote = not in_single_quote
            out.append(c)
        elif c == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            out.append(c)
        elif c == '?' and not in_single_quote and not in_double_quote:
            out.append('%s')
        else:
            out.append(c)
        i += 1
    return "".join(out)


class PostgresCursorWrapper:
    """
    Wraps a psycopg2 cursor to provide a drop-in SQLite-compatible interface:
    - Translates '?' placeholders to '%s' via adapt_sql_for_pg.
    - Emulates cursor.lastrowid on INSERT queries using RETURNING id.
    - Supports row access by column name via RealDictRow.
    """
    def __init__(self, pg_cursor, connection_wrapper=None):
        self._cursor = pg_cursor
        self._conn_wrapper = connection_wrapper
        self.lastrowid = None

    def execute(self, sql: str, params: Any = None):
        adapted = adapt_sql_for_pg(sql)
        trimmed = adapted.strip()
        is_insert = trimmed.upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in trimmed.upper()
        
        # If it is an INSERT into a table and lacks RETURNING, add it to capture lastrowid
        should_add_returning = is_insert and not has_returning
        if should_add_returning:
            adapted = trimmed.rstrip(";").strip() + " RETURNING id;"

        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            self._cursor.execute(adapted, params)
        else:
            self._cursor.execute(adapted)

        if should_add_returning:
            try:
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = row.get("id") if isinstance(row, dict) else row[0]
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = None
            
        return self

    def executemany(self, sql: str, seq_of_parameters: Any):
        adapted = adapt_sql_for_pg(sql)
        return self._cursor.executemany(adapted, seq_of_parameters)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iter__(self):
        return iter(self._cursor)


class PostgresConnectionWrapper:
    """
    Wraps a psycopg2 connection to provide SQLite-compatible semantics:
    - Returns PostgresCursorWrapper with RealDictCursor.
    - Manages context manager commit/rollback.
    """
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresCursorWrapper(cur, self)

    def execute(self, sql: str, params: Any = None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


# ==============================================================================
# DATABASE CONNECTION MANAGEMENT (HYBRID POSTGRESQL / SQLITE)
# ==============================================================================
def get_db_connection(db_path: Optional[str] = None):
    """
    Establish a connection to either:
    1. Supabase / PostgreSQL cloud database if DATABASE_URL or SUPABASE_DB_URL is set (and db_path is None).
    2. SQLite database with row factory, foreign key constraints, and WAL journal mode enabled.
    """
    if is_postgres_configured(db_path):
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError(
                "PostgreSQL / Supabase connection requested (DATABASE_URL is set), "
                "but 'psycopg2' is not installed. Please run: pip install psycopg2-binary"
            )
        raw_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
        # Normalize postgres:// to postgresql:// for psycopg2
        if raw_url.startswith("postgres://"):
            raw_url = "postgresql://" + raw_url[len("postgres://"):]
        
        try:
            conn = psycopg2.connect(
                raw_url,
                sslmode="require",
                connect_timeout=15,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            return PostgresConnectionWrapper(conn)
        except Exception as err:
            print(f"[ERROR] [Supabase/PostgreSQL] Connection failed: {err}")
            raise
    else:
        path = db_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        conn = sqlite3.connect(path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn


# ==============================================================================
# HAVERSINE DISTANCE & GEOSPATIAL FUNCTIONS
# ==============================================================================
def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two coordinates in kilometers.
    """
    R = 6371.0  # Earth's mean radius in km
    
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))
    
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    distance_km = R * c
    return round(distance_km, 3)


def init_postgres_db(conn) -> None:
    """
    Initialize PostgreSQL / Supabase tables, indexes, and initial seed records.
    """
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            district TEXT,
            role TEXT NOT NULL DEFAULT 'Citizen' CHECK(role IN ('Citizen', 'Volunteer', 'Authority_Admin')),
            is_verified INT NOT NULL DEFAULT 0,
            is_email_verified INT NOT NULL DEFAULT 0,
            email_otp TEXT,
            email_otp_expires_at TIMESTAMP WITH TIME ZONE,
            credibility_score INT NOT NULL DEFAULT 100,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Incident Reports Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_reports (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            hazard_type TEXT NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lng DOUBLE PRECISION NOT NULL,
            description TEXT,
            image_url TEXT,
            severity INT NOT NULL DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'verified', 'rejected', 'resolved', 'cleared')),
            cluster_id TEXT,
            verified_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
            ai_confidence DOUBLE PRECISION,
            ai_hazard_type TEXT,
            ai_severity INT,
            ai_summary TEXT,
            is_flagged_spam INT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Relief Shelters Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relief_shelters (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lng DOUBLE PRECISION NOT NULL,
            capacity INT NOT NULL DEFAULT 100 CHECK(capacity >= 0),
            occupied INT NOT NULL DEFAULT 0 CHECK(occupied >= 0),
            contact_number TEXT,
            district TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'full', 'standby', 'closed')),
            in_charge_name TEXT,
            in_charge_phone TEXT,
            supplies_json TEXT,
            amenities_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. Missing Persons Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missing_persons (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INT,
            gender TEXT,
            last_known_location TEXT,
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            contact_phone TEXT,
            photo_url TEXT,
            medical_needs TEXT,
            status TEXT NOT NULL DEFAULT 'missing' CHECK(status IN ('missing', 'search_in_progress', 'located_safe', 'hospitalized')),
            located_at_shelter_id BIGINT REFERENCES relief_shelters(id) ON DELETE SET NULL,
            reported_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 5. Family Safety Contacts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_safety_contacts (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            contact_name TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            relationship TEXT,
            last_ping_status TEXT,
            last_ping_lat DOUBLE PRECISION,
            last_ping_lng DOUBLE PRECISION,
            last_ping_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 6. Volunteer Missions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volunteer_missions (
            id BIGSERIAL PRIMARY KEY,
            cluster_id TEXT NOT NULL,
            volunteer_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'dispatched' CHECK(status IN ('dispatched', 'en_route', 'on_site', 'verified', 'resolved')),
            assigned_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 7. Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            action TEXT NOT NULL,
            actor_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            target_id BIGINT,
            details TEXT,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 8. Emergency Broadcasts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_broadcasts (
            id BIGSERIAL PRIMARY KEY,
            broadcast_id TEXT UNIQUE NOT NULL,
            hazard_type TEXT NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lng DOUBLE PRECISION NOT NULL,
            radius_km DOUBLE PRECISION NOT NULL,
            alert_en TEXT NOT NULL,
            alert_ml TEXT NOT NULL,
            recipients_count INT DEFAULT 0,
            sender TEXT,
            telegram_link TEXT,
            whatsapp_link TEXT,
            sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_reports_status ON incident_reports(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_reports_coords ON incident_reports(lat, lng);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relief_shelters_coords ON relief_shelters(lat, lng);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_broadcasts_sent ON emergency_broadcasts(sent_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_broadcasts_bid ON emergency_broadcasts(broadcast_id);")

    conn.commit()
    seed_initial_data(conn)


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize database tables, indexes, dynamic column migrations,
    and seed default records (supports both PostgreSQL/Supabase and SQLite).
    """
    if is_postgres_configured(db_path):
        conn = get_db_connection(db_path)
        try:
            init_postgres_db(conn)
            print("[OK] [Database] Supabase / PostgreSQL Engine & Schema initialized successfully.")
        finally:
            conn.close()
        return

    target_path = db_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    
    with get_db_connection(target_path) as conn:
        cursor = conn.cursor()
        
        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                lat REAL,
                lng REAL,
                district TEXT,
                role TEXT NOT NULL DEFAULT 'Citizen' CHECK(role IN ('Citizen', 'Volunteer', 'Authority_Admin')),
                is_verified INTEGER NOT NULL DEFAULT 0,
                is_email_verified INTEGER NOT NULL DEFAULT 0,
                email_otp TEXT,
                email_otp_expires_at TIMESTAMP,
                credibility_score INTEGER NOT NULL DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Incident Reports Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incident_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                hazard_type TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                description TEXT,
                image_url TEXT,
                severity INTEGER NOT NULL DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'verified', 'rejected', 'resolved', 'cleared')),
                cluster_id TEXT,
                verified_by INTEGER,
                ai_confidence REAL,
                ai_hazard_type TEXT,
                ai_severity INTEGER,
                ai_summary TEXT,
                is_flagged_spam INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL
            );
        """)
        
        # Migrations for incident_reports
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='incident_reports';")
        master_row = cursor.fetchone()
        if master_row and "resolved" not in master_row["sql"]:
            cursor.execute("ALTER TABLE incident_reports RENAME TO incident_reports_old;")
            cursor.execute("""
                CREATE TABLE incident_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    hazard_type TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    description TEXT,
                    image_url TEXT,
                    severity INTEGER NOT NULL DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'verified', 'rejected', 'resolved', 'cleared')),
                    cluster_id TEXT,
                    verified_by INTEGER,
                    ai_confidence REAL,
                    ai_hazard_type TEXT,
                    ai_severity INTEGER,
                    ai_summary TEXT,
                    is_flagged_spam INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL
                );
            """)
            cursor.execute("""
                INSERT INTO incident_reports (id, user_id, hazard_type, lat, lng, description, image_url, severity, status, cluster_id, verified_by, ai_confidence, ai_hazard_type, ai_severity, ai_summary, is_flagged_spam, created_at, updated_at)
                SELECT id, user_id, hazard_type, lat, lng, description, image_url, severity, status, cluster_id, verified_by, ai_confidence, ai_hazard_type, ai_severity, ai_summary, is_flagged_spam, created_at, updated_at
                FROM incident_reports_old;
            """)
            cursor.execute("DROP TABLE incident_reports_old;")

        cursor.execute("PRAGMA table_info(incident_reports);")
        inc_cols = [col["name"] for col in cursor.fetchall()]
        if "severity" not in inc_cols:
            cursor.execute("ALTER TABLE incident_reports ADD COLUMN severity INTEGER NOT NULL DEFAULT 3;")
        if "ai_confidence" not in inc_cols:
            cursor.execute("ALTER TABLE incident_reports ADD COLUMN ai_confidence REAL;")
        if "ai_hazard_type" not in inc_cols:
            cursor.execute("ALTER TABLE incident_reports ADD COLUMN ai_hazard_type TEXT;")
        if "ai_severity" not in inc_cols:
            cursor.execute("ALTER TABLE incident_reports ADD COLUMN ai_severity INTEGER;")
        if "ai_summary" not in inc_cols:
            cursor.execute("ALTER TABLE incident_reports ADD COLUMN ai_summary TEXT;")
        if "is_flagged_spam" not in inc_cols:
            cursor.execute("ALTER TABLE incident_reports ADD COLUMN is_flagged_spam INTEGER DEFAULT 0;")
            
        # 3. Relief Shelters Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relief_shelters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 100 CHECK(capacity >= 0),
                occupied INTEGER NOT NULL DEFAULT 0 CHECK(occupied >= 0),
                contact_number TEXT,
                district TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'full', 'standby', 'closed')),
                in_charge_name TEXT,
                in_charge_phone TEXT,
                supplies_json TEXT,
                amenities_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Migrations for relief_shelters
        cursor.execute("PRAGMA table_info(relief_shelters);")
        shelter_cols = [col["name"] for col in cursor.fetchall()]
        if "status" not in shelter_cols:
            cursor.execute("ALTER TABLE relief_shelters ADD COLUMN status TEXT NOT NULL DEFAULT 'active';")
        if "in_charge_name" not in shelter_cols:
            cursor.execute("ALTER TABLE relief_shelters ADD COLUMN in_charge_name TEXT;")
        if "in_charge_phone" not in shelter_cols:
            cursor.execute("ALTER TABLE relief_shelters ADD COLUMN in_charge_phone TEXT;")
        if "supplies_json" not in shelter_cols:
            cursor.execute("ALTER TABLE relief_shelters ADD COLUMN supplies_json TEXT;")
        if "amenities_json" not in shelter_cols:
            cursor.execute("ALTER TABLE relief_shelters ADD COLUMN amenities_json TEXT;")
        if "created_at" not in shelter_cols:
            cursor.execute("ALTER TABLE relief_shelters ADD COLUMN created_at TIMESTAMP;")
            
        # 4. Missing Persons Registry Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missing_persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                last_known_location TEXT,
                lat REAL,
                lng REAL,
                contact_phone TEXT,
                photo_url TEXT,
                medical_needs TEXT,
                status TEXT NOT NULL DEFAULT 'missing' CHECK(status IN ('missing', 'search_in_progress', 'located_safe', 'hospitalized')),
                located_at_shelter_id INTEGER,
                reported_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (located_at_shelter_id) REFERENCES relief_shelters(id) ON DELETE SET NULL,
                FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            );
        """)
        
        # 5. Family Safety Circle Contacts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_safety_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                relationship TEXT,
                last_ping_status TEXT,
                last_ping_lat REAL,
                last_ping_lng REAL,
                last_ping_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        
        # 6. Field Volunteer Missions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id TEXT NOT NULL,
                volunteer_id INTEGER,
                status TEXT NOT NULL DEFAULT 'dispatched' CHECK(status IN ('dispatched', 'en_route', 'on_site', 'verified', 'resolved')),
                assigned_by INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (volunteer_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
            );
        """)
        
        # 7. Audit Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                actor_id INTEGER,
                target_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
            );
        """)
        
        # 8. Emergency Broadcasts Table (Persistent Alert History)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id TEXT UNIQUE NOT NULL,
                hazard_type TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                radius_km REAL NOT NULL,
                alert_en TEXT NOT NULL,
                alert_ml TEXT NOT NULL,
                recipients_count INTEGER DEFAULT 0,
                sender TEXT,
                telegram_link TEXT,
                whatsapp_link TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 9. Indexes for fast geospatial, operational, and alert queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_reports_status ON incident_reports(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_reports_coords ON incident_reports(lat, lng);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incident_reports_cluster ON incident_reports(cluster_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relief_shelters_district ON relief_shelters(district);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relief_shelters_coords ON relief_shelters(lat, lng);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relief_shelters_status ON relief_shelters(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_missing_persons_status ON missing_persons(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_family_safety_user ON family_safety_contacts(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_volunteer_missions_status ON volunteer_missions(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_broadcasts_sent_at ON emergency_broadcasts(sent_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emergency_broadcasts_bcast_id ON emergency_broadcasts(broadcast_id);")
        
        # Schema Migration: Ensure is_verified and email columns exist
        cursor.execute("PRAGMA table_info(users);")
        user_cols = [row[1] for row in cursor.fetchall()]
        if "is_verified" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0;")
        if "email" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT;")
        if "is_email_verified" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN is_email_verified INTEGER NOT NULL DEFAULT 0;")
        if "email_otp" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN email_otp TEXT;")
        if "email_otp_expires_at" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN email_otp_expires_at TIMESTAMP;")

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone) WHERE phone IS NOT NULL;")
            
        # Authority Admins and NDRF Volunteers are verified officials by default
        cursor.execute("UPDATE users SET is_verified = 1 WHERE role IN ('Authority_Admin', 'Volunteer');")
        
        # Clear any legacy static home coordinates so only live location is utilized
        cursor.execute("UPDATE users SET lat = NULL, lng = NULL, district = NULL;")
        
        conn.commit()
        seed_initial_data(conn, db_path=target_path)


# ==============================================================================
# SEED DATA
# ==============================================================================
def seed_initial_data(conn: Optional[sqlite3.Connection] = None, db_path: Optional[str] = None) -> None:
    """Seed initial Authority Admin, Kerala relief shelters, and sample registries."""
    should_close = False
    if conn is None:
        conn = get_db_connection(db_path)
        should_close = True
        
    try:
        cursor = conn.cursor()
        
        # 1. Seed Default Authority Admin (Abhinav)
        admin_phone = "+916282115954"
        admin_email = "admin@terrarisk.gov.in"
        admin_hash = hash_password("A12345678")
        cursor.execute("SELECT id FROM users WHERE phone = ? OR email = ? LIMIT 1;", (admin_phone, admin_email))
        admin_row = cursor.fetchone()
        if not admin_row:
            cursor.execute("""
                INSERT INTO users (name, phone, email, password_hash, lat, lng, district, role, is_verified, is_email_verified, credibility_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                "Abhinav (KSDMA Authority Admin)",
                admin_phone,
                admin_email,
                admin_hash,
                None,
                None,
                None,
                "Authority_Admin",
                1,
                1,
                100
            ))
            admin_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO audit_logs (action, actor_id, target_id, details)
                VALUES (?, ?, ?, ?);
            """, (
                "SYSTEM_INIT_SEED_ADMIN",
                admin_id,
                admin_id,
                "Default Authority Admin (Abhinav) initialized."
            ))
            print(f"[OK] Initialized default Authority Admin (Abhinav, ID: {admin_id})")
        else:
            cursor.execute("""
                UPDATE users SET name = 'Abhinav (KSDMA Authority Admin)', email = ?, role = 'Authority_Admin', is_verified = 1, is_email_verified = 1, credibility_score = 100, password_hash = ?, lat = NULL, lng = NULL, district = NULL
                WHERE phone = ? OR email = ?;
            """, (admin_email, admin_hash, admin_phone, admin_email))

        # 1b. Seed Authority Incident Commander (Used by automated drills)
        cmd_phone = "+919999900000"
        cmd_email = "commander@terrarisk.gov.in"
        cmd_hash = hash_password("Admin@Terra2026!")
        cursor.execute("SELECT id FROM users WHERE phone = ? OR email = ? LIMIT 1;", (cmd_phone, cmd_email))
        cmd_row = cursor.fetchone()
        if not cmd_row:
            cursor.execute("""
                INSERT INTO users (name, phone, email, password_hash, lat, lng, district, role, is_verified, is_email_verified, credibility_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                "KSDMA Incident Commander",
                cmd_phone,
                cmd_email,
                cmd_hash,
                None,
                None,
                None,
                "Authority_Admin",
                1,
                1,
                100
            ))
        else:
            cursor.execute("""
                UPDATE users SET name = 'KSDMA Incident Commander', email = ?, role = 'Authority_Admin', is_verified = 1, is_email_verified = 1, password_hash = ?
                WHERE phone = ? OR email = ?;
            """, (cmd_email, cmd_hash, cmd_phone, cmd_email))

        # 2. Seed Default Field Volunteer
        vol_phone = "+919888800000"
        vol_email = "volunteer@terrarisk.org"
        vol_hash = hash_password("Volunteer@2026!")
        cursor.execute("SELECT id FROM users WHERE phone = ? OR email = ? LIMIT 1;", (vol_phone, vol_email))
        vol_row = cursor.fetchone()
        if not vol_row:
            cursor.execute("""
                INSERT INTO users (name, phone, email, password_hash, lat, lng, district, role, is_verified, is_email_verified, credibility_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                "Anandhu Nair (NDRF Volunteer)",
                vol_phone,
                vol_email,
                vol_hash,
                None,
                None,
                None,
                "Volunteer",
                1,
                1,
                100
            ))
        else:
            cursor.execute("""
                UPDATE users SET role = 'Volunteer', email = ?, is_verified = 1, is_email_verified = 1, password_hash = ?, lat = NULL, lng = NULL, district = NULL
                WHERE phone = ? OR email = ?;
            """, (vol_email, vol_hash, vol_phone, vol_email))

        # 3. Seed Default Sample Citizen (For quick evaluator logins)
        cit_phone = "+919847012345"
        cit_email = "citizen@terrarisk.org"
        cit_hash = hash_password("SecurePassword123!")
        cursor.execute("SELECT id FROM users WHERE phone = ? OR email = ? LIMIT 1;", (cit_phone, cit_email))
        cit_row = cursor.fetchone()
        if not cit_row:
            cursor.execute("""
                INSERT INTO users (name, phone, email, password_hash, lat, lng, district, role, is_verified, is_email_verified, credibility_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                "Abhinav R (Citizen)",
                cit_phone,
                cit_email,
                cit_hash,
                None,
                None,
                None,
                "Citizen",
                1,
                1,
                100
            ))
        else:
            cursor.execute("""
                UPDATE users SET email = ?, is_email_verified = 1, password_hash = ?, lat = NULL, lng = NULL, district = NULL
                WHERE phone = ? OR email = ?;
            """, (cit_email, cit_hash, cit_phone, cit_email))

        # 4. Seed Sample Kerala Relief Shelters (At least 10 shelters across Wayanad, Idukki, Malappuram, Kozhikode)
        cursor.execute("SELECT COUNT(*) AS count FROM relief_shelters;")
        if cursor.fetchone()["count"] < 10:
            sample_shelters = [
                (
                    "Meppadi Community Relief Center", 11.5510, 76.1280, 400, 85, "+914936282220", "Wayanad", "active",
                    "Rajesh Kumar (Deputy Tahsildar)", "+919447123456",
                    json.dumps({"water_litres": 3200, "food_packets": 650, "medical_kits": 45, "infant_supplies": 30, "fuel_litres": 250}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Kalpetta SKMJ Higher Secondary Camp", 11.6080, 76.0825, 600, 120, "+914936202444", "Wayanad", "active",
                    "Dr. Sunitha Menon", "+919447654321",
                    json.dumps({"water_litres": 4500, "food_packets": 1100, "medical_kits": 80, "infant_supplies": 50, "fuel_litres": 400}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Mananthavady Govt High School Shelter", 11.8020, 76.0030, 300, 30, "+914935240222", "Wayanad", "active",
                    "K. V. Mathew (Revenue Inspector)", "+919447789012",
                    json.dumps({"water_litres": 1800, "food_packets": 400, "medical_kits": 25, "infant_supplies": 15, "fuel_litres": 150}),
                    json.dumps({"medical_post": False, "power_backup": True, "wheelchair_accessible": False, "child_care": True})
                ),
                (
                    "Sulthan Bathery St. Mary's Relief Camp", 11.6620, 76.2570, 350, 45, "+914936220333", "Wayanad", "active",
                    "Fr. George Thomas", "+919447334455",
                    json.dumps({"water_litres": 2200, "food_packets": 500, "medical_kits": 30, "infant_supplies": 20, "fuel_litres": 180}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Munnar Govt Arts College Relief Camp", 10.0889, 77.0595, 450, 110, "+914865230230", "Idukki", "active",
                    "P. Murugan (Village Officer)", "+919446112233",
                    json.dumps({"water_litres": 2800, "food_packets": 550, "medical_kits": 35, "infant_supplies": 20, "fuel_litres": 300}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Devikulam Community Hall Shelter", 10.0620, 77.1040, 300, 40, "+914865264210", "Idukki", "active",
                    "S. Ramaswamy (Tahsildar)", "+919446223344",
                    json.dumps({"water_litres": 2000, "food_packets": 450, "medical_kits": 25, "infant_supplies": 15, "fuel_litres": 200}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": False, "child_care": True})
                ),
                (
                    "Adimali Govt Vocational Higher Secondary Camp", 10.0450, 76.9550, 400, 70, "+914864222100", "Idukki", "active",
                    "Biju Varghese (Panchayat Officer)", "+919446334455",
                    json.dumps({"water_litres": 2500, "food_packets": 600, "medical_kits": 40, "infant_supplies": 25, "fuel_litres": 220}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Nilambur Govt Higher Secondary Camp", 11.2770, 76.2240, 500, 95, "+914831220456", "Malappuram", "active",
                    "Muhammed Faisal (Panchayat Sec.)", "+919446889900",
                    json.dumps({"water_litres": 3500, "food_packets": 800, "medical_kits": 50, "infant_supplies": 35, "fuel_litres": 350}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Eranad Knowledge City Relief Shelter", 11.1950, 76.1220, 550, 60, "+914832734500", "Malappuram", "active",
                    "Abdul Rasheed (Coordinator)", "+919446990011",
                    json.dumps({"water_litres": 4000, "food_packets": 900, "medical_kits": 60, "infant_supplies": 40, "fuel_litres": 300}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Kozhikode Medical College Relief Camp", 11.2725, 75.8360, 700, 150, "+914952350212", "Kozhikode", "active",
                    "Dr. K. Narayanan (Superintendent)", "+919447445566",
                    json.dumps({"water_litres": 6000, "food_packets": 1400, "medical_kits": 120, "infant_supplies": 80, "fuel_litres": 500}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                ),
                (
                    "Thamarassery GHSS Emergency Shelter", 11.4167, 75.9333, 380, 50, "+914952223400", "Kozhikode", "active",
                    "Smt. Leela Damodaran", "+919447556677",
                    json.dumps({"water_litres": 2600, "food_packets": 520, "medical_kits": 35, "infant_supplies": 20, "fuel_litres": 200}),
                    json.dumps({"medical_post": True, "power_backup": True, "wheelchair_accessible": True, "child_care": True})
                )
            ]
            
            cursor.executemany("""
                INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, sample_shelters)
            print(f"[OK] Seeded {len(sample_shelters)} relief shelters.")

        # 4. Seed Sample Missing Persons Entry
        cursor.execute("SELECT COUNT(*) AS count FROM missing_persons;")
        if cursor.fetchone()["count"] == 0:
            sample_missing = [
                ("Pranav Varma", 28, "Male", "Chooralmala Tea Estate Section 4", 11.5361, 76.1667, "+919876543210", None, "Requires insulin", "missing", None, 1),
                ("Kalyani Amma", 67, "Female", "Mundakkai Riverbank settlement", 11.5167, 76.1500, "+919876543211", None, "Mobility impaired", "search_in_progress", None, 1)
            ]
            cursor.executemany("""
                INSERT INTO missing_persons (name, age, gender, last_known_location, lat, lng, contact_phone, photo_url, medical_needs, status, located_at_shelter_id, reported_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, sample_missing)

        conn.commit()
    finally:
        if should_close:
            conn.close()


# ==============================================================================
# USER MANAGEMENT & REPUTATION
# ==============================================================================
def get_user_by_phone(phone: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ? LIMIT 1;", (phone.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_email = email.strip().lower()
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ? LIMIT 1;", (clean_email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_identifier(identifier: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Look up user by either email address or phone number."""
    ident = identifier.strip()
    if "@" in ident:
        return get_user_by_email(ident, db_path=db_path)

    # Phone normalization for search
    digits = re.sub(r"[\s\-]", "", ident)
    if digits.startswith("+91"):
        core = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        core = digits[2:]
    else:
        core = digits.lstrip("+")
    normalized = "+91" + core if re.match(r"^[6-9]\d{9}$", core) else ident
    return get_user_by_phone(normalized, db_path=db_path)


def get_user_by_id(user_id: int, include_password: bool = False, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ? LIMIT 1;", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        u_dict = dict(row)
        if not include_password:
            u_dict.pop("password_hash", None)
            u_dict.pop("email_otp", None)
        return u_dict
    finally:
        conn.close()


def create_user(
    name: str,
    phone: Optional[str] = None,
    password_hash: str = "",
    email: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    district: Optional[str] = None,
    role: str = "Citizen",
    is_verified: int = 0,
    is_email_verified: int = 0,
    email_otp: Optional[str] = None,
    email_otp_expires_at: Optional[str] = None,
    credibility_score: int = 100,
    db_path: Optional[str] = None
) -> int:
    valid_roles = ("Citizen", "Volunteer", "Authority_Admin")
    if role not in valid_roles:
        role = "Citizen"
    if role in ("Authority_Admin", "Volunteer"):
        is_verified = 1
        is_email_verified = 1
        
    clean_phone = phone.strip() if phone else None
    clean_email = email.strip().lower() if email else None
    if email_otp and not email_otp_expires_at:
        email_otp_expires_at = (datetime.utcnow() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                name, phone, email, password_hash, lat, lng, district,
                role, is_verified, is_email_verified, email_otp, email_otp_expires_at, credibility_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            name.strip(), clean_phone, clean_email, password_hash,
            lat, lng, district, role, is_verified, is_email_verified,
            email_otp, email_otp_expires_at, credibility_score
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_unverified_user(
    user_id: int,
    name: str,
    phone: Optional[str] = None,
    password_hash: str = "",
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    district: Optional[str] = None,
    role: str = "Citizen",
    email_otp: Optional[str] = None,
    email_otp_expires_at: Optional[str] = None,
    db_path: Optional[str] = None
) -> bool:
    """Update details and refresh OTP for an existing unverified user registration."""
    clean_phone = phone.strip() if phone else None
    if email_otp and not email_otp_expires_at:
        email_otp_expires_at = (datetime.utcnow() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET name = ?, phone = ?, password_hash = ?, lat = ?, lng = ?, district = ?,
                role = ?, email_otp = ?, email_otp_expires_at = ?
            WHERE id = ? AND is_email_verified = 0 AND is_verified = 0;
        """, (
            name.strip(), clean_phone, password_hash, lat, lng, district,
            role, email_otp, email_otp_expires_at, user_id
        ))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_unverified_user(user_id: int, db_path: Optional[str] = None) -> bool:
    """Safely delete an unverified pending registration."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ? AND is_email_verified = 0 AND is_verified = 0;", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def set_email_otp(
    user_id: int,
    otp: str,
    expires_in_minutes: int = 10,
    db_path: Optional[str] = None
) -> bool:
    """Store or refresh 6-digit email OTP for a user with expiration."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        expires_at = (datetime.utcnow() + timedelta(minutes=expires_in_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE users
            SET email_otp = ?, email_otp_expires_at = ?
            WHERE id = ?;
        """, (otp.strip(), expires_at, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def verify_email_otp(
    email: str,
    code: str,
    db_path: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify submitted 6-digit OTP against active token in database."""
    clean_email = email.strip().lower()
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ? LIMIT 1;", (clean_email,))
        row = cursor.fetchone()
        if not row:
            return False, "No profile found associated with this email address.", None
        user = dict(row)

        if user.get("is_email_verified"):
            return True, "Email is already verified.", get_user_by_id(user["id"], db_path=db_path)

        saved_otp = user.get("email_otp")
        expires_at_str = user.get("email_otp_expires_at")

        if not saved_otp or not expires_at_str:
            return False, "No active verification code found. Please request a new code.", None

        if str(code).strip() != str(saved_otp).strip():
            return False, "Invalid verification code. Please check your email and try again.", None

        try:
            if isinstance(expires_at_str, datetime):
                expires_at = expires_at_str.replace(tzinfo=None)
            else:
                expires_at = datetime.strptime(str(expires_at_str).split(".")[0].replace("Z", ""), "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() > expires_at:
                return False, "Verification code has expired. Please request a new code.", None
        except Exception:
            pass

        cursor.execute("""
            UPDATE users
            SET is_email_verified = 1, email_otp = NULL, email_otp_expires_at = NULL
            WHERE id = ?;
        """, (user["id"],))
        conn.commit()

        verified_user = get_user_by_id(user["id"], db_path=db_path)
        return True, "Email address verified successfully.", verified_user
    finally:
        conn.close()


def set_user_verification(user_id: int, is_verified: bool = True, db_path: Optional[str] = None) -> bool:
    """Directly verify or revoke verification for a user by Authority Admin."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_verified = ? WHERE id = ?;", (1 if is_verified else 0, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_user_credibility(user_id: int, new_score: int, db_path: Optional[str] = None) -> bool:
    """Legacy compatibility helper."""
    clamped_score = max(0, min(100, new_score))
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET credibility_score = ? WHERE id = ?;", (clamped_score, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_users_in_radius(
    lat: float,
    lng: float,
    radius_km: float,
    role: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        query = "SELECT id, name, phone, lat, lng, district, role, credibility_score, created_at FROM users WHERE lat IS NOT NULL AND lng IS NOT NULL"
        params = []
        if role:
            query += " AND role = ?"
            params.append(role)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            u_dict = dict(row)
            dist = calculate_haversine_distance(lat, lng, u_dict["lat"], u_dict["lng"])
            if dist <= radius_km:
                u_dict["distance_km"] = dist
                results.append(u_dict)
        results.sort(key=lambda x: x["distance_km"])
        return results
    finally:
        conn.close()


# ==============================================================================
# RELIEF SHELTER & INVENTORY MANAGEMENT (CRUD)
# ==============================================================================
def create_relief_shelter(
    name: str,
    lat: float,
    lng: float,
    capacity: int,
    contact_number: str,
    district: str,
    in_charge_name: Optional[str] = None,
    in_charge_phone: Optional[str] = None,
    supplies_dict: Optional[Dict[str, Any]] = None,
    amenities_dict: Optional[Dict[str, Any]] = None,
    status: str = "active",
    db_path: Optional[str] = None
) -> int:
    """Create a new relief camp record with inventory and amenities."""
    default_supplies = {
        "water_litres": 2000,
        "food_packets": 500,
        "medical_kits": 30,
        "infant_supplies": 20,
        "fuel_litres": 150
    }
    final_supplies = supplies_dict or default_supplies
    default_amenities = {
        "medical_post": True,
        "power_backup": True,
        "wheelchair_accessible": True,
        "child_care": True
    }
    final_amenities = amenities_dict or default_amenities

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?);
        """, (
            name.strip(),
            float(lat),
            float(lng),
            int(capacity),
            contact_number.strip(),
            district.strip(),
            status,
            in_charge_name or "",
            in_charge_phone or "",
            json.dumps(final_supplies),
            json.dumps(final_amenities)
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_relief_shelter(
    shelter_id: int,
    name: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    capacity: Optional[int] = None,
    contact_number: Optional[str] = None,
    district: Optional[str] = None,
    in_charge_name: Optional[str] = None,
    in_charge_phone: Optional[str] = None,
    status: Optional[str] = None,
    supplies_dict: Optional[Dict[str, Any]] = None,
    amenities_dict: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> bool:
    """Update relief shelter parameters, capacity, and operational status."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        fields = []
        values = []
        if name is not None:
            fields.append("name = ?"); values.append(name.strip())
        if lat is not None:
            fields.append("lat = ?"); values.append(float(lat))
        if lng is not None:
            fields.append("lng = ?"); values.append(float(lng))
        if capacity is not None:
            fields.append("capacity = ?"); values.append(int(capacity))
        if contact_number is not None:
            fields.append("contact_number = ?"); values.append(contact_number.strip())
        if district is not None:
            fields.append("district = ?"); values.append(district.strip())
        if in_charge_name is not None:
            fields.append("in_charge_name = ?"); values.append(in_charge_name.strip())
        if in_charge_phone is not None:
            fields.append("in_charge_phone = ?"); values.append(in_charge_phone.strip())
        if status is not None:
            fields.append("status = ?"); values.append(status.strip())
        if supplies_dict is not None:
            fields.append("supplies_json = ?"); values.append(json.dumps(supplies_dict))
        if amenities_dict is not None:
            fields.append("amenities_json = ?"); values.append(json.dumps(amenities_dict))
            
        if not fields:
            return False
            
        values.append(shelter_id)
        cursor.execute(f"UPDATE relief_shelters SET {', '.join(fields)} WHERE id = ?;", values)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_relief_shelter(shelter_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a relief shelter record."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relief_shelters WHERE id = ?;", (shelter_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_shelter_supplies(shelter_id: int, supplies_dict: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Update emergency supplies inventory for a relief camp."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, supplies_json FROM relief_shelters WHERE id = ?;", (shelter_id,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Relief shelter not found."}
            
        current = {}
        if row["supplies_json"]:
            try: current = json.loads(row["supplies_json"])
            except Exception: pass
            
        current.update(supplies_dict)
        cursor.execute("UPDATE relief_shelters SET supplies_json = ? WHERE id = ?;", (json.dumps(current), shelter_id))
        conn.commit()
        return {"success": True, "shelter_id": shelter_id, "name": row["name"], "supplies": current}
    finally:
        conn.close()


def get_shelter_by_id(shelter_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, lat, lng, capacity, occupied, contact_number, district,
                   status, in_charge_name, in_charge_phone, supplies_json, amenities_json, created_at
            FROM relief_shelters WHERE id = ?;
        """, (shelter_id,))
        row = cursor.fetchone()
        if not row:
            return None
        s = dict(row)
        s["available_capacity"] = max(0, s["capacity"] - s["occupied"])
        s["available_spots"] = s["available_capacity"]
        s["occupancy_rate_pct"] = round((s["occupied"] / s["capacity"] * 100.0), 1) if s["capacity"] > 0 else 0.0
        try: s["supplies"] = json.loads(s["supplies_json"]) if s["supplies_json"] else {}
        except Exception: s["supplies"] = {}
        try: s["amenities"] = json.loads(s["amenities_json"]) if s["amenities_json"] else {}
        except Exception: s["amenities"] = {}
        return s
    finally:
        conn.close()


def update_shelter_occupancy(shelter_id: int, occupied: int, db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, capacity, occupied FROM relief_shelters WHERE id = ?;", (shelter_id,))
        shelter = cursor.fetchone()
        if not shelter:
            return {"success": False, "error": "Relief shelter not found."}
            
        capacity = shelter["capacity"]
        clamped_occupied = max(0, min(capacity, int(occupied)))
        
        # If full, auto-update status
        new_status = "full" if clamped_occupied >= capacity else "active"
        cursor.execute("UPDATE relief_shelters SET occupied = ?, status = ? WHERE id = ?;", (clamped_occupied, new_status, shelter_id))
        conn.commit()
        
        available = max(0, capacity - clamped_occupied)
        occupancy_rate = round((clamped_occupied / capacity * 100.0), 1) if capacity > 0 else 0.0
        
        return {
            "success": True,
            "shelter_id": shelter_id,
            "name": shelter["name"],
            "capacity": capacity,
            "occupied": clamped_occupied,
            "available_spots": available,
            "occupancy_rate_pct": occupancy_rate,
            "status": new_status
        }
    finally:
        conn.close()


def get_nearby_shelters(
    lat: float,
    lng: float,
    radius_km: Optional[float] = None,
    district: Optional[str] = None,
    status: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT id, name, lat, lng, capacity, occupied, contact_number, district,
                   status, in_charge_name, in_charge_phone, supplies_json, amenities_json, created_at
            FROM relief_shelters WHERE 1=1
        """
        params = []
        if district:
            query += " AND LOWER(district) = LOWER(?)"
            params.append(district)
        if status:
            query += " AND status = ?"
            params.append(status)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            shelter = dict(row)
            dist = calculate_haversine_distance(lat, lng, shelter["lat"], shelter["lng"])
            if radius_km is None or dist <= radius_km:
                shelter["distance_km"] = round(dist, 2)
                shelter["available_capacity"] = max(0, shelter["capacity"] - shelter["occupied"])
                shelter["available_spots"] = shelter["available_capacity"]
                shelter["occupancy_rate_pct"] = round((shelter["occupied"] / shelter["capacity"] * 100.0), 1) if shelter["capacity"] > 0 else 0.0
                try: shelter["supplies"] = json.loads(shelter["supplies_json"]) if shelter["supplies_json"] else {}
                except Exception: shelter["supplies"] = {}
                try: shelter["amenities"] = json.loads(shelter["amenities_json"]) if shelter["amenities_json"] else {}
                except Exception: shelter["amenities"] = {}
                results.append(shelter)
                
        results.sort(key=lambda x: x["distance_km"])
        return results
    finally:
        conn.close()


# ==============================================================================
# AUDIT LOGGING
# ==============================================================================
def log_audit_action(
    action: str,
    actor_id: Optional[int] = None,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (action, actor_id, target_id, details, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (action, actor_id, target_id, details))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ==============================================================================
# INCIDENT REPORTING & SPATIAL AUTO-CLUSTERING
# ==============================================================================
def find_nearby_pending_cluster(
    lat: float,
    lng: float,
    radius_km: float = 0.5,
    hours_window: float = 2.0,
    db_path: Optional[str] = None
) -> Optional[str]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cutoff_dt = datetime.utcnow() - timedelta(hours=float(hours_window))
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            SELECT id, lat, lng, cluster_id, created_at
            FROM incident_reports
            WHERE status IN ('pending', 'verified')
              AND created_at >= ?;
        """, (cutoff_str,))
        rows = cursor.fetchall()
        
        for row in rows:
            dist = calculate_haversine_distance(lat, lng, row["lat"], row["lng"])
            if dist <= radius_km:
                if row["cluster_id"]:
                    return row["cluster_id"]
                else:
                    new_cluster_id = f"clust_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"
                    cursor.execute("UPDATE incident_reports SET cluster_id = ? WHERE id = ?;", (new_cluster_id, row["id"]))
                    conn.commit()
                    return new_cluster_id
        return None
    finally:
        conn.close()


def check_and_autoverify_cluster(
    cluster_id: str,
    threshold: int = 5,
    db_path: Optional[str] = None
) -> Tuple[bool, int]:
    """
    Auto-verify an incident cluster if >= threshold reports (or distinct reporters)
    have reported an incident in the same 500m area cluster.
    Returns (is_verified, report_count).
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, status FROM incident_reports
            WHERE cluster_id = ? AND status IN ('pending', 'verified');
        """, (cluster_id,))
        rows = cursor.fetchall()
        if not rows:
            return False, 0

        total_reports = len(rows)
        unique_users = {r["user_id"] for r in rows if r["user_id"] is not None}
        distinct_count = max(len(unique_users), total_reports)

        if distinct_count >= threshold:
            pending_ids = [r["id"] for r in rows if r["status"] == 'pending']
            if pending_ids:
                cursor.execute(f"""
                    UPDATE incident_reports
                    SET status = 'verified', verified_by = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({','.join(['?'] * len(pending_ids))});
                """, pending_ids)

                user_ids_to_verify = list(unique_users)
                if user_ids_to_verify:
                    cursor.execute(f"""
                        UPDATE users SET is_verified = 1
                        WHERE id IN ({','.join(['?'] * len(user_ids_to_verify))});
                    """, user_ids_to_verify)

                cursor.execute("""
                    INSERT INTO audit_logs (action, actor_id, target_id, details)
                    VALUES (?, NULL, ?, ?);
                """, (
                    "INCIDENT_CLUSTER_AUTOVERIFIED",
                    pending_ids[0],
                    f"Cluster {cluster_id} automatically verified after reaching crowd consensus threshold ({distinct_count} reports >= {threshold})."
                ))
                conn.commit()
            return True, distinct_count
        return False, distinct_count
    finally:
        conn.close()


def create_incident_report(
    user_id: int,
    hazard_type: str,
    lat: float,
    lng: float,
    description: Optional[str] = None,
    severity: int = 3,
    image_url: Optional[str] = None,
    cluster_id: Optional[str] = None,
    status: str = "pending",
    ai_confidence: Optional[float] = None,
    ai_hazard_type: Optional[str] = None,
    ai_severity: Optional[int] = None,
    ai_summary: Optional[str] = None,
    is_flagged_spam: int = 0,
    db_path: Optional[str] = None
) -> int:
    valid_hazards = ('mud_crack', 'stream_overflow', 'rockfall', 'blocked_road', 'slope_movement')
    if hazard_type not in valid_hazards:
        hazard_type = 'mud_crack'
    severity = max(1, min(5, int(severity)))
    
    if not cluster_id:
        cluster_id = f"clust_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"
        
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incident_reports (
                user_id, hazard_type, lat, lng, description, image_url, severity, status, cluster_id,
                ai_confidence, ai_hazard_type, ai_severity, ai_summary, is_flagged_spam
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id, hazard_type, lat, lng, description, image_url, severity, status, cluster_id,
            ai_confidence, ai_hazard_type, ai_severity, ai_summary, is_flagged_spam
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_nearby_incidents(
    lat: float,
    lng: float,
    radius_km: float,
    status: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT r.id, r.user_id, r.hazard_type, r.lat, r.lng, r.description,
                   r.image_url, r.severity, r.status, r.cluster_id, r.verified_by,
                   r.ai_confidence, r.ai_hazard_type, r.ai_severity, r.ai_summary, r.is_flagged_spam,
                   r.created_at, r.updated_at,
                   u.name AS reporter_name, u.is_verified AS reporter_is_verified
            FROM incident_reports r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND r.status = ?"
            params.append(status)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            inc_dict = dict(row)
            dist = calculate_haversine_distance(lat, lng, inc_dict["lat"], inc_dict["lng"])
            if dist <= radius_km:
                inc_dict["distance_km"] = dist
                results.append(inc_dict)
        results.sort(key=lambda x: x["distance_km"])
        return results
    finally:
        conn.close()


def get_active_incident_clusters(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT r.id, r.user_id, r.hazard_type, r.lat, r.lng, r.description,
                   r.image_url, r.severity, r.status, r.cluster_id, r.verified_by,
                   r.ai_confidence, r.ai_hazard_type, r.ai_severity, r.ai_summary, r.is_flagged_spam,
                   r.created_at, r.updated_at,
                   u.name AS reporter_name, u.role AS reporter_role, u.is_verified AS reporter_is_verified
            FROM incident_reports r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.status IN ('pending', 'verified')
            ORDER BY r.created_at DESC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        clusters_map = {}
        for row in rows:
            r = dict(row)
            c_id = r["cluster_id"] or f"single_{r['id']}"
            if c_id not in clusters_map:
                clusters_map[c_id] = {
                    "cluster_id": c_id,
                    "reports": [],
                    "hazard_types": [],
                    "severities": [],
                    "lats": [],
                    "lngs": [],
                    "has_verified": False,
                    "max_ai_confidence": 0.0,
                    "latest_created_at": r["created_at"]
                }
            clusters_map[c_id]["reports"].append(r)
            clusters_map[c_id]["hazard_types"].append(r["hazard_type"])
            clusters_map[c_id]["severities"].append(r["severity"] if r["severity"] is not None else 3)
            clusters_map[c_id]["lats"].append(r["lat"])
            clusters_map[c_id]["lngs"].append(r["lng"])
            if r.get("ai_confidence") and r["ai_confidence"] > clusters_map[c_id]["max_ai_confidence"]:
                clusters_map[c_id]["max_ai_confidence"] = r["ai_confidence"]
            if r["status"] == "verified":
                clusters_map[c_id]["has_verified"] = True
                if r.get("verified_by") is None:
                    clusters_map[c_id]["is_auto_verified"] = True
                
        cluster_results = []
        for c_id, c in clusters_map.items():
            rep_count = len(c["reports"])
            avg_lat = sum(c["lats"]) / rep_count
            avg_lng = sum(c["lngs"]) / rep_count
            avg_sev = sum(c["severities"]) / rep_count
            max_sev = max(c["severities"])
            primary_hazard = max(set(c["hazard_types"]), key=c["hazard_types"].count)
            latest_report = c["reports"][0]
            
            cluster_results.append({
                "cluster_id": c_id,
                "primary_hazard_type": primary_hazard,
                "hazard_types": list(set(c["hazard_types"])),
                "lat": round(avg_lat, 5),
                "lng": round(avg_lng, 5),
                "report_count": rep_count,
                "avg_severity": round(avg_sev, 1),
                "max_severity": max_sev,
                "max_ai_confidence": round(c["max_ai_confidence"], 2),
                "status": "verified" if c["has_verified"] else "pending",
                "is_auto_verified": c.get("is_auto_verified", False) or (c["has_verified"] and rep_count >= 5),
                "description": latest_report["description"] or f"Cluster of {rep_count} {primary_hazard.replace('_', ' ')} reports",
                "created_at": c["latest_created_at"],
                "reports": c["reports"]
            })
            
        cluster_results.sort(key=lambda x: (
            1 if x["status"] == "verified" else 0,
            x["report_count"],
            x["max_severity"],
            x["created_at"]
        ), reverse=True)
        return cluster_results
    finally:
        conn.close()


def get_pending_incident_clusters(db_path: Optional[str] = None, status_filter: str = "all") -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if status_filter == "pending":
            status_clause = "r.status = 'pending'"
        elif status_filter == "verified":
            status_clause = "r.status = 'verified'"
        else:
            status_clause = "r.status IN ('pending', 'verified')"
            
        query = f"""
            SELECT r.id, r.user_id, r.hazard_type, r.lat, r.lng, r.description,
                   r.image_url, r.severity, r.status, r.cluster_id, r.verified_by, r.created_at,
                   r.ai_confidence, r.ai_hazard_type, r.ai_severity, r.ai_summary, r.is_flagged_spam,
                   u.name AS reporter_name, u.phone AS reporter_phone,
                   u.role AS reporter_role, u.is_verified AS reporter_is_verified
            FROM incident_reports r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE {status_clause}
            ORDER BY r.created_at DESC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        clusters_map = {}
        for row in rows:
            r = dict(row)
            c_id = r["cluster_id"] or f"single_{r['id']}"
            if c_id not in clusters_map:
                clusters_map[c_id] = {
                    "cluster_id": c_id,
                    "reports": [],
                    "hazard_types": [],
                    "severities": [],
                    "lats": [],
                    "lngs": [],
                    "max_ai_confidence": 0.0,
                    "ai_summaries": [],
                    "has_spam_flag": False,
                    "has_verified": False,
                    "latest_created_at": r["created_at"]
                }
            clusters_map[c_id]["reports"].append(r)
            clusters_map[c_id]["hazard_types"].append(r["hazard_type"])
            clusters_map[c_id]["severities"].append(r["severity"] if r["severity"] is not None else 3)
            clusters_map[c_id]["lats"].append(r["lat"])
            clusters_map[c_id]["lngs"].append(r["lng"])
            if r.get("ai_confidence") and r["ai_confidence"] > clusters_map[c_id]["max_ai_confidence"]:
                clusters_map[c_id]["max_ai_confidence"] = r["ai_confidence"]
            if r.get("ai_summary"):
                clusters_map[c_id]["ai_summaries"].append(r["ai_summary"])
            if r.get("is_flagged_spam"):
                clusters_map[c_id]["has_spam_flag"] = True
            if r.get("status") == "verified":
                clusters_map[c_id]["has_verified"] = True
                
        pending_results = []
        for c_id, c in clusters_map.items():
            rep_count = len(c["reports"])
            avg_lat = sum(c["lats"]) / rep_count
            avg_lng = sum(c["lngs"]) / rep_count
            avg_sev = sum(c["severities"]) / rep_count
            max_sev = max(c["severities"])
            verified_rep_count = sum(1 for r in c["reports"] if r.get("reporter_is_verified"))
            primary_hazard = max(set(c["hazard_types"]), key=c["hazard_types"].count)
            is_verified = c["has_verified"]
            priority_score = round((rep_count * 15.0) + (avg_sev * 12.0) + (verified_rep_count * 10.0) + (c["max_ai_confidence"] * 20.0) + (10.0 if is_verified else 0.0), 1)
            
            latest_report = c["reports"][0]
            ai_summary_text = c["ai_summaries"][0] if c["ai_summaries"] else ("High visual hazard indicator" if c["max_ai_confidence"] >= 0.7 else "Standard field report")
            
            pending_results.append({
                "cluster_id": c_id,
                "primary_hazard_type": primary_hazard,
                "lat": round(avg_lat, 5),
                "lng": round(avg_lng, 5),
                "report_count": rep_count,
                "avg_severity": round(avg_sev, 1),
                "max_severity": max_sev,
                "verified_reporters_count": verified_rep_count,
                "priority_score": priority_score,
                "max_ai_confidence": round(c["max_ai_confidence"], 2),
                "ai_summary": ai_summary_text,
                "has_spam_flag": c["has_spam_flag"],
                "status": "verified" if is_verified else "pending",
                "description": latest_report["description"] or f"{primary_hazard.replace('_', ' ').title()} near sector ({avg_lat:.3f}N, {avg_lng:.3f}E)",
                "created_at": c["latest_created_at"],
                "reports": c["reports"]
            })
            
        pending_results.sort(key=lambda x: (1 if x["status"] == "pending" else 0, x["priority_score"]), reverse=True)
        return pending_results
    finally:
        conn.close()


def verify_incident_cluster(
    cluster_id: str,
    verified_by_user_id: int,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    numeric_id = int(cluster_id) if str(cluster_id).isdigit() else -1
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, hazard_type, severity
            FROM incident_reports
            WHERE (cluster_id = ? OR id = ?) AND status = 'pending';
        """, (str(cluster_id), numeric_id))
        reports = cursor.fetchall()
        
        if not reports:
            cursor.execute("SELECT id FROM incident_reports WHERE cluster_id = ? OR id = ?;", (str(cluster_id), numeric_id))
            if cursor.fetchone():
                return {"success": False, "error": "Incident cluster has already been verified or rejected."}
            return {"success": False, "error": "Incident cluster not found."}
            
        report_ids = [r["id"] for r in reports]
        unique_user_ids = list({r["user_id"] for r in reports if r["user_id"] is not None})
        
        cursor.execute(f"""
            UPDATE incident_reports
            SET status = 'verified', verified_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({','.join(['?'] * len(report_ids))});
        """, [verified_by_user_id] + report_ids)
        
        # Admin verification also verifies reporting citizens
        if unique_user_ids:
            cursor.execute(f"""
                UPDATE users SET is_verified = 1
                WHERE id IN ({','.join(['?'] * len(unique_user_ids))});
            """, unique_user_ids)
                
        cursor.execute("""
            INSERT INTO audit_logs (action, actor_id, target_id, details)
            VALUES (?, ?, ?, ?);
        """, (
            "INCIDENT_CLUSTER_VERIFIED",
            verified_by_user_id,
            report_ids[0],
            f"Cluster {cluster_id} ({len(report_ids)} reports) verified by Authority Admin ID {verified_by_user_id}."
        ))
        conn.commit()
        return {
            "success": True,
            "message": f"Cluster {cluster_id} verified by Authority Admin.",
            "cluster_id": cluster_id,
            "verified_reports_count": len(report_ids),
            "verified_citizens_count": len(unique_user_ids)
        }
    finally:
        conn.close()


def reject_incident_cluster(
    cluster_id: str,
    rejected_by_user_id: int,
    reason: str = "False Alarm / Duplicate",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    numeric_id = int(cluster_id) if str(cluster_id).isdigit() else -1
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, hazard_type, severity
            FROM incident_reports
            WHERE (cluster_id = ? OR id = ?) AND status = 'pending';
        """, (str(cluster_id), numeric_id))
        reports = cursor.fetchall()
        
        if not reports:
            cursor.execute("SELECT id FROM incident_reports WHERE cluster_id = ? OR id = ?;", (str(cluster_id), numeric_id))
            if cursor.fetchone():
                return {"success": False, "error": "Incident cluster is already processed."}
            return {"success": False, "error": "Incident cluster not found."}
            
        report_ids = [r["id"] for r in reports]
        
        cursor.execute(f"""
            UPDATE incident_reports
            SET status = 'rejected', verified_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({','.join(['?'] * len(report_ids))});
        """, [rejected_by_user_id] + report_ids)
        
        cursor.execute("""
            INSERT INTO audit_logs (action, actor_id, target_id, details)
            VALUES (?, ?, ?, ?);
        """, (
            "INCIDENT_CLUSTER_REJECTED",
            rejected_by_user_id,
            report_ids[0],
            f"Cluster {cluster_id} marked as rejected (Reason: {reason})."
        ))
        conn.commit()
        return {
            "success": True,
            "message": f"Cluster {cluster_id} rejected ({reason}).",
            "cluster_id": cluster_id,
            "rejected_reports_count": len(report_ids),
            "reason": reason
        }
    finally:
        conn.close()


def resolve_incident_cluster(
    cluster_id: str,
    resolved_by_user_id: int,
    notes: str = "Site Cleared / Hazard Mitigated",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Mark an active or verified incident cluster as resolved/cleared once the disaster site is safe."""
    numeric_id = int(cluster_id) if str(cluster_id).isdigit() else -1
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, hazard_type, severity, status
            FROM incident_reports
            WHERE (cluster_id = ? OR id = ?) AND status IN ('pending', 'verified');
        """, (str(cluster_id), numeric_id))
        reports = cursor.fetchall()
        
        if not reports:
            cursor.execute("SELECT id, status FROM incident_reports WHERE cluster_id = ? OR id = ?;", (str(cluster_id), numeric_id))
            row = cursor.fetchone()
            if row:
                return {"success": False, "error": f"Incident is already {row['status']}."}
            return {"success": False, "error": "Incident cluster not found."}
            
        report_ids = [r["id"] for r in reports]
        
        cursor.execute(f"""
            UPDATE incident_reports
            SET status = 'resolved', updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({','.join(['?'] * len(report_ids))});
        """, report_ids)
        
        cursor.execute("""
            INSERT INTO audit_logs (action, actor_id, target_id, details)
            VALUES (?, ?, ?, ?);
        """, (
            "INCIDENT_CLUSTER_RESOLVED",
            resolved_by_user_id,
            report_ids[0],
            f"Cluster {cluster_id} marked as RESOLVED (Site Cleared). Notes: {notes}."
        ))
        conn.commit()
        return {
            "success": True,
            "message": f"Cluster {cluster_id} marked as resolved/cleared. Removed from active map.",
            "cluster_id": cluster_id,
            "resolved_reports_count": len(report_ids),
            "notes": notes
        }
    finally:
        conn.close()



# ==============================================================================
# MISSING PERSONS & RESCUE REQUEST REGISTRY
# ==============================================================================
def create_missing_person(
    name: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    last_known_location: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    contact_phone: Optional[str] = None,
    photo_url: Optional[str] = None,
    medical_needs: Optional[str] = None,
    reported_by_user_id: Optional[int] = None,
    db_path: Optional[str] = None
) -> int:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO missing_persons (name, age, gender, last_known_location, lat, lng, contact_phone, photo_url, medical_needs, status, reported_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'missing', ?);
        """, (name.strip(), age, gender, last_known_location, lat, lng, contact_phone, photo_url, medical_needs, reported_by_user_id))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_missing_persons(
    status: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        sql = """
            SELECT m.id, m.name, m.age, m.gender, m.last_known_location, m.lat, m.lng,
                   m.contact_phone, m.photo_url, m.medical_needs, m.status,
                   m.located_at_shelter_id, m.reported_by_user_id, m.created_at, m.updated_at,
                   s.name AS located_shelter_name, s.district AS shelter_district
            FROM missing_persons m
            LEFT JOIN relief_shelters s ON m.located_at_shelter_id = s.id
            WHERE 1=1
        """
        params = []
        if status:
            sql += " AND m.status = ?"
            params.append(status)
        if query:
            sql += " AND (LOWER(m.name) LIKE ? OR LOWER(m.last_known_location) LIKE ?)"
            params.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
            
        sql += " ORDER BY m.created_at DESC LIMIT ?;"
        params.append(limit)
        cursor.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_missing_person_by_id(person_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.name, m.age, m.gender, m.last_known_location, m.lat, m.lng,
                   m.contact_phone, m.photo_url, m.medical_needs, m.status,
                   m.located_at_shelter_id, m.reported_by_user_id, m.created_at, m.updated_at,
                   s.name AS located_shelter_name, s.district AS shelter_district
            FROM missing_persons m
            LEFT JOIN relief_shelters s ON m.located_at_shelter_id = s.id
            WHERE m.id = ?;
        """, (person_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_missing_person_status(
    person_id: int,
    status: str,
    located_at_shelter_id: Optional[int] = None,
    db_path: Optional[str] = None
) -> bool:
    valid_statuses = ('missing', 'search_in_progress', 'located_safe', 'hospitalized')
    if status not in valid_statuses:
        status = 'located_safe'
        
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE missing_persons
            SET status = ?, located_at_shelter_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (status, located_at_shelter_id, person_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()




# ==============================================================================
# FIELD VOLUNTEER MISSIONS
# ==============================================================================
def create_volunteer_mission(
    cluster_id: str,
    volunteer_id: Optional[int],
    assigned_by: int,
    notes: Optional[str] = None,
    db_path: Optional[str] = None
) -> int:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO volunteer_missions (cluster_id, volunteer_id, status, assigned_by, notes)
            VALUES (?, ?, 'dispatched', ?, ?);
        """, (cluster_id, volunteer_id, assigned_by, notes))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_volunteer_missions(
    volunteer_id: Optional[int] = None,
    status: Optional[str] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        sql = """
            SELECT m.id, m.cluster_id, m.volunteer_id, m.status, m.assigned_by, m.notes, m.created_at, m.updated_at,
                   u.name AS volunteer_name, u.phone AS volunteer_phone,
                   adm.name AS assigner_name
            FROM volunteer_missions m
            LEFT JOIN users u ON m.volunteer_id = u.id
            LEFT JOIN users adm ON m.assigned_by = adm.id
            WHERE 1=1
        """
        params = []
        if volunteer_id:
            sql += " AND m.volunteer_id = ?"
            params.append(volunteer_id)
        if status:
            sql += " AND m.status = ?"
            params.append(status)
        sql += " ORDER BY m.created_at DESC;"
        cursor.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def update_volunteer_mission_status(
    mission_id: int,
    status: str,
    notes: Optional[str] = None,
    db_path: Optional[str] = None
) -> bool:
    valid_statuses = ('dispatched', 'en_route', 'on_site', 'verified', 'resolved')
    if status not in valid_statuses:
        status = 'verified'
        
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if notes:
            cursor.execute("""
                UPDATE volunteer_missions
                SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (status, notes, mission_id))
        else:
            cursor.execute("""
                UPDATE volunteer_missions
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (status, mission_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ==============================================================================
# AUTHORITY DASHBOARD METRICS
# ==============================================================================
def get_authority_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        total_pending = cursor.execute("SELECT COUNT(*) AS c FROM incident_reports WHERE status = 'pending';").fetchone()["c"]
        pending_clusters = cursor.execute("SELECT COUNT(DISTINCT cluster_id) AS c FROM incident_reports WHERE status = 'pending';").fetchone()["c"]
        total_verified = cursor.execute("SELECT COUNT(*) AS c FROM incident_reports WHERE status = 'verified';").fetchone()["c"]
        total_rejected = cursor.execute("SELECT COUNT(*) AS c FROM incident_reports WHERE status = 'rejected';").fetchone()["c"]
        
        active_volunteers = cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'Volunteer';").fetchone()["c"]
        total_citizens = cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'Citizen';").fetchone()["c"]
        total_shelters = cursor.execute("SELECT COUNT(*) AS c FROM relief_shelters;").fetchone()["c"]
        missing_count = cursor.execute("SELECT COUNT(*) AS c FROM missing_persons WHERE status = 'missing';").fetchone()["c"]
        active_missions = cursor.execute("SELECT COUNT(*) AS c FROM volunteer_missions WHERE status IN ('dispatched', 'en_route', 'on_site');").fetchone()["c"]
        audit_count = cursor.execute("SELECT COUNT(*) AS c FROM audit_logs;").fetchone()["c"]
        
        return {
            "total_pending_reports": total_pending,
            "pending_clusters_count": pending_clusters,
            "active_verified_hazards": total_verified,
            "rejected_false_alarms": total_rejected,
            "active_field_volunteers": active_volunteers,
            "registered_citizens": total_citizens,
            "relief_shelters_count": total_shelters,
            "active_missing_persons": missing_count,
            "active_volunteer_missions": active_missions,
            "total_audit_actions": audit_count,
            "synced_at": datetime.utcnow().isoformat() + "Z"
        }
    finally:
        conn.close()


def save_emergency_broadcast(record: Dict[str, Any], db_path: Optional[str] = None) -> bool:
    """Persist an emergency broadcast record into database (compatible with SQLite and PostgreSQL)."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emergency_broadcasts (
                broadcast_id, hazard_type, lat, lng, radius_km,
                alert_en, alert_ml, recipients_count, sender,
                telegram_link, whatsapp_link, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (broadcast_id) DO UPDATE SET
                hazard_type = excluded.hazard_type,
                lat = excluded.lat,
                lng = excluded.lng,
                radius_km = excluded.radius_km,
                alert_en = excluded.alert_en,
                alert_ml = excluded.alert_ml,
                recipients_count = excluded.recipients_count,
                sender = excluded.sender,
                telegram_link = excluded.telegram_link,
                whatsapp_link = excluded.whatsapp_link,
                sent_at = excluded.sent_at;
        """, (
            record.get("broadcast_id"),
            record.get("hazard_type", "slope_movement"),
            float(record.get("lat", 0.0)),
            float(record.get("lng", 0.0)),
            float(record.get("radius_km", 5.0)),
            record.get("alert_en", ""),
            record.get("alert_ml", ""),
            int(record.get("recipients_count", 0)),
            record.get("sender", "KSDMA Emergency Command"),
            record.get("telegram_link", ""),
            record.get("whatsapp_link", ""),
            record.get("sent_at") or datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save emergency broadcast: {e}")
        return False
    finally:
        conn.close()


def get_persisted_emergency_broadcasts(hours_window: float = 24.0, limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent active emergency broadcasts from persistent database."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cutoff = (datetime.utcnow() - timedelta(hours=hours_window)).isoformat()
        cursor.execute("""
            SELECT * FROM emergency_broadcasts
            WHERE sent_at >= ?
            ORDER BY id DESC
            LIMIT ?;
        """, (cutoff, limit))
        rows = cursor.fetchall()
        broadcasts = []
        for r in rows:
            broadcasts.append({
                "broadcast_id": r["broadcast_id"],
                "hazard_type": r["hazard_type"],
                "lat": r["lat"],
                "lng": r["lng"],
                "radius_km": r["radius_km"],
                "alert_en": r["alert_en"],
                "alert_ml": r["alert_ml"],
                "recipients_count": r["recipients_count"],
                "sender": r["sender"],
                "telegram_link": r["telegram_link"],
                "whatsapp_link": r["whatsapp_link"],
                "sent_at": r["sent_at"]
            })
        return broadcasts
    except Exception as e:
        print(f"[ERROR] Failed to fetch persisted broadcasts: {e}")
        return []
    finally:
        conn.close()


def get_database_info(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Return runtime diagnostic telemetry about the connected database."""
    is_pg = is_postgres_configured(db_path)
    engine_name = "PostgreSQL (Supabase)" if is_pg else "SQLite (Local File)"
    
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        users_count = cursor.execute("SELECT COUNT(*) AS c FROM users;").fetchone()["c"]
        incidents_count = cursor.execute("SELECT COUNT(*) AS c FROM incident_reports;").fetchone()["c"]
        shelters_count = cursor.execute("SELECT COUNT(*) AS c FROM relief_shelters;").fetchone()["c"]
        missing_count = cursor.execute("SELECT COUNT(*) AS c FROM missing_persons;").fetchone()["c"]
        audit_count = cursor.execute("SELECT COUNT(*) AS c FROM audit_logs;").fetchone()["c"]
        
        return {
            "engine": engine_name,
            "is_cloud_supabase": is_pg,
            "connected": True,
            "tables": {
                "users": users_count,
                "incident_reports": incidents_count,
                "relief_shelters": shelters_count,
                "missing_persons": missing_count,
                "audit_logs": audit_count
            }
        }
    except Exception as e:
        return {
            "engine": engine_name,
            "is_cloud_supabase": is_pg,
            "connected": False,
            "error": str(e)
        }
    finally:
        conn.close()


if __name__ == "__main__":
    print("[INFO] Initializing TerraRisk AI Database...")
    init_db()
    if is_postgres_configured():
        print("[OK] Database verified: Connected to Supabase / PostgreSQL cloud instance.")
    else:
        print(f"[OK] Database verified: Connected to SQLite at {DEFAULT_DB_PATH}")
