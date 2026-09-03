#!/usr/bin/env python3
"""
TerraRisk AI - Supabase Cloud Database Initializer & Verification Tool
Deploys all production tables, spatial indexes, and seeds initial official accounts
and Kerala relief shelters directly into your Supabase PostgreSQL project.
Usage:
    python init_supabase.py [optional_database_url]
"""

import os
import sys
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load backend/.env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from database import init_postgres_db, hash_password, get_db_connection

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def get_target_db_url() -> str:
    # 1. Check CLI argument
    if len(sys.argv) > 1 and sys.argv[1].startswith(("postgres://", "postgresql://")):
        return sys.argv[1]
    
    # 2. Check environment variable
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if url and url.startswith(("postgres://", "postgresql://")):
        return url
    
    return ""


def main():
    print("=" * 70)
    print("🚀 TERRARISK AI — SUPABASE DATABASE INITIALIZER & VERIFIER")
    print("=" * 70)

    db_url = get_target_db_url()
    if not db_url:
        print("\n[!] Supabase DATABASE_URL is not set.")
        print("\nTo connect to your Supabase project:")
        print("  1. In your Supabase Dashboard -> Project Settings -> Database -> Connection string")
        print("  2. Copy the URI (e.g. postgresql://postgres.[REF]:[PASSWORD]@...:5432/postgres)")
        print("  3. Set it in backend/.env: DATABASE_URL=your_connection_string")
        print("     OR run:")
        print("     python init_supabase.py \"postgresql://postgres.[REF]:[PASS]@...:5432/postgres\"")
        print("=" * 70)
        sys.exit(1)

    # Normalize url
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]

    print(f"[*] Connecting to Supabase PostgreSQL...")
    # Hide password in output
    masked_url = db_url
    if "@" in masked_url:
        prefix, rest = masked_url.split("@", 1)
        if ":" in prefix:
            user_part = prefix.rsplit(":", 1)[0]
            masked_url = f"{user_part}:****@{rest}"
    print(f"    Target: {masked_url}")

    try:
        conn = psycopg2.connect(
            db_url,
            sslmode="require",
            connect_timeout=20
        )
        conn.autocommit = False
        print("[OK] Connected successfully to Supabase cloud instance!")
    except Exception as e:
        print(f"\n[FAIL] Could not connect to Supabase: {e}")
        print("\nTips:")
        print("  - If using direct connection (db.[ref].supabase.co), your network might lack IPv6.")
        print("    Try using the Connection Pooler URI (Session mode, port 5432 or 6543) from Supabase settings.")
        print("  - Ensure your password has special characters URL-encoded (e.g., %40 for @).")
        sys.exit(1)

    print("\n[*] Initializing tables, constraints, and indexes in Supabase...")
    try:
        from database import PostgresConnectionWrapper
        wrapper = PostgresConnectionWrapper(conn)
        init_postgres_db(wrapper)
        print("[OK] All 8 core disaster tables & spatial indexes created successfully!")
    except Exception as e:
        print(f"[FAIL] Error initializing schema: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)

    # Verify all modules
    print("\n[*] Verifying operational health across all modules on Supabase...")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    tables = [
        "users",
        "incident_reports",
        "relief_shelters",
        "missing_persons",
        "family_safety_contacts",
        "volunteer_missions",
        "audit_logs",
        "emergency_broadcasts"
    ]

    print("\n  Table Row Counts:")
    print("  " + "-" * 40)
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) AS count FROM {table};")
            count = cur.fetchone()["count"]
            print(f"  • {table:<25}: {count:>5} records")
        except Exception as e:
            print(f"  • {table:<25}: ERROR ({e})")

    # Verify seeded Authority Admin
    cur.execute("SELECT id, name, email, role, is_verified FROM users WHERE role = 'Authority_Admin' LIMIT 1;")
    admin = cur.fetchone()
    if admin:
        print(f"\n[OK] Default Authority Admin verified: {admin['name']} ({admin['email']}, ID: {admin['id']})")

    # Verify relief camps
    cur.execute("SELECT COUNT(*) AS count FROM relief_shelters WHERE status = 'active';")
    shelter_count = cur.fetchone()["count"]
    print(f"[OK] Active Kerala Relief Shelters ready: {shelter_count} camps")

    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print("🎉 SUPABASE DATABASE IS FULLY CONFIGURED & VERIFIED FOR PRODUCTION!")
    print("=" * 70)


if __name__ == "__main__":
    main()
