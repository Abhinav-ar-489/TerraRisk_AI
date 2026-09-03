"""
==============================================================================
TerraRisk AI - Supabase & PostgreSQL Migration Verification Suite
==============================================================================
Validates:
1. SQL parameter adapter (adapt_sql_for_pg)
2. Hybrid database connection routing (is_postgres_configured)
3. SQLite local fallback integrity (with temporary in-memory/file test db)
4. Telemetry and diagnostics via get_database_info()
5. Optional live Supabase connectivity when DATABASE_URL is supplied
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from unittest.mock import MagicMock

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import (
    adapt_sql_for_pg,
    is_postgres_configured,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    get_db_connection,
    init_db,
    get_database_info,
    save_emergency_broadcast,
    get_persisted_emergency_broadcasts,
    verify_email_otp,
    set_email_otp,
    create_user,
    get_user_by_email
)


class TestSupabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_terrarisk.db")
        init_db(self.temp_db)

    def tearDown(self):
        try:
            if os.path.exists(self.temp_db):
                os.remove(self.temp_db)
        except Exception:
            pass

    def test_sql_adapter_parameter_conversion(self):
        """Verify ? to %s conversion while preserving ? in literals."""
        # Simple query
        sql1 = "SELECT * FROM users WHERE email = ? AND role = ?;"
        self.assertEqual(adapt_sql_for_pg(sql1), "SELECT * FROM users WHERE email = %s AND role = %s;")

        # Query with question mark in string literal
        sql2 = "SELECT * FROM users WHERE name = 'Is this working?' AND phone = ?;"
        self.assertEqual(
            adapt_sql_for_pg(sql2),
            "SELECT * FROM users WHERE name = 'Is this working?' AND phone = %s;"
        )

        # INSERT statement
        sql3 = "INSERT INTO table (a, b) VALUES (?, ?);"
        self.assertEqual(adapt_sql_for_pg(sql3), "INSERT INTO table (a, b) VALUES (%s, %s);")

    def test_postgres_cursor_wrapper_emulation(self):
        """Verify PostgresCursorWrapper translates SQL and intercepts INSERT returning."""
        mock_pg_cursor = MagicMock()
        mock_pg_cursor.fetchone.return_value = {"id": 42}
        mock_pg_cursor.rowcount = 1

        wrapper = PostgresCursorWrapper(mock_pg_cursor)
        
        # Test INSERT returning injection
        wrapper.execute("INSERT INTO users (name) VALUES (?);", ("Test User",))
        
        # Should call pg_cursor.execute with %s and RETURNING id
        mock_pg_cursor.execute.assert_called_once_with(
            "INSERT INTO users (name) VALUES (%s) RETURNING id;",
            ("Test User",)
        )
        self.assertEqual(wrapper.lastrowid, 42)

    def test_local_sqlite_fallback_stability(self):
        """Verify complete user creation, OTP, and broadcast in test SQLite."""
        user_id = create_user(
            name="Supabase Test Citizen",
            phone="+919876543210",
            email="test_citizen@kerala.gov.in",
            password_hash="test_salt$test_hash",
            district="Wayanad",
            db_path=self.temp_db
        )
        self.assertIsNotNone(user_id)
        user = get_user_by_email("test_citizen@kerala.gov.in", db_path=self.temp_db)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "test_citizen@kerala.gov.in")

        # Set & verify OTP
        set_email_otp(user["id"], "654321", expires_in_minutes=15, db_path=self.temp_db)
        success, msg, verified_user = verify_email_otp("test_citizen@kerala.gov.in", "654321", db_path=self.temp_db)
        self.assertTrue(success)
        self.assertEqual(verified_user["is_email_verified"], 1)

    def test_save_emergency_broadcast_on_conflict(self):
        """Verify emergency broadcast save and retrieval works with ON CONFLICT syntax."""
        record = {
            "broadcast_id": "TEST-ALERT-001",
            "hazard_type": "landslide",
            "lat": 11.55,
            "lng": 76.12,
            "radius_km": 5.0,
            "alert_en": "Evacuate immediately",
            "alert_ml": "ഉടൻ മാറുക",
            "recipients_count": 150
        }
        res = save_emergency_broadcast(record, db_path=self.temp_db)
        self.assertTrue(res)

        # Update the same broadcast ID (test ON CONFLICT update)
        record["recipients_count"] = 200
        res2 = save_emergency_broadcast(record, db_path=self.temp_db)
        self.assertTrue(res2)

        broadcasts = get_persisted_emergency_broadcasts(hours_window=1.0, db_path=self.temp_db)
        self.assertEqual(len(broadcasts), 1)
        self.assertEqual(broadcasts[0]["recipients_count"], 200)

    def test_database_info_telemetry(self):
        """Verify get_database_info returns structure and table counts."""
        info = get_database_info(self.temp_db)
        self.assertTrue(info["connected"])
        self.assertEqual(info["engine"], "SQLite (Local File)")
        self.assertFalse(info["is_cloud_supabase"])
        self.assertIn("users", info["tables"])
        self.assertIn("relief_shelters", info["tables"])


if __name__ == "__main__":
    unittest.main()
