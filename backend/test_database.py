"""
TerraRisk AI - Phase 1 Verification Suite
Tests SQLite database schema, constraints, spatial queries, seeding, and server integration.
"""

import os
import sys
import tempfile
import unittest
import math

# Force UTF-8 encoding on Windows console streams if available
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import (
    init_db,
    get_db_connection,
    seed_initial_data,
    calculate_haversine_distance,
    get_users_in_radius,
    get_nearby_incidents,
    get_nearby_shelters,
    log_audit_action,
    hash_password,
    verify_password,
    DEFAULT_DB_PATH
)
from server import app


class TestPhase1DatabaseArchitecture(unittest.TestCase):
    def setUp(self):
        """Create an isolated temporary SQLite database for test runs."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)
        self.app = app.test_client()

    def tearDown(self):
        """Close and cleanup temporary database file."""
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    def test_01_schema_and_tables_exist(self):
        """Verify all 4 required tables and indexes are created properly."""
        conn = get_db_connection(self.temp_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        
        required_tables = ["users", "incident_reports", "relief_shelters", "audit_logs"]
        for table in required_tables:
            self.assertIn(table, tables, f"Missing table: {table}")
            
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = [row["name"] for row in cursor.fetchall()]
        required_indexes = [
            "idx_users_phone",
            "idx_incident_reports_status",
            "idx_incident_reports_coords",
            "idx_relief_shelters_coords",
            "idx_relief_shelters_district",
            "idx_audit_logs_timestamp"
        ]
        for idx in required_indexes:
            self.assertIn(idx, indexes, f"Missing index: {idx}")
            
        conn.close()

    def test_02_password_hashing_and_verification(self):
        """Verify PBKDF2 password hashing and constant-time verification."""
        password = "Admin@Terra2026!"
        hashed = hash_password(password)
        
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))
        self.assertNotEqual(password, hashed)

    def test_03_default_seed_data(self):
        """Verify default Authority Admin and Kerala relief shelters are seeded."""
        conn = get_db_connection(self.temp_db_path)
        cursor = conn.cursor()
        
        # Check Authority Admin
        cursor.execute("SELECT * FROM users WHERE role = 'Authority_Admin';")
        admin = cursor.fetchone()
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "Authority_Admin")
        self.assertEqual(admin["credibility_score"], 100)
        self.assertTrue(verify_password("A12345678", admin["password_hash"]) or verify_password("Admin@Terra2026!", admin["password_hash"]))
        
        # Check Relief Shelters
        cursor.execute("SELECT COUNT(*) AS count FROM relief_shelters;")
        shelter_count = cursor.fetchone()["count"]
        self.assertGreaterEqual(shelter_count, 10)
        
        # Check districts represented
        cursor.execute("SELECT DISTINCT district FROM relief_shelters;")
        districts = [row["district"] for row in cursor.fetchall()]
        self.assertIn("Wayanad", districts)
        self.assertIn("Idukki", districts)
        self.assertIn("Malappuram", districts)
        self.assertIn("Kozhikode", districts)
        
        # Check Audit Log for seed action
        cursor.execute("SELECT * FROM audit_logs WHERE action = 'SYSTEM_INIT_SEED_ADMIN';")
        audit_entry = cursor.fetchone()
        self.assertIsNotNone(audit_entry)
        
        conn.close()

    def test_04_haversine_distance_calculation(self):
        """Verify Haversine distance accuracy between known coordinates."""
        # Chooralmala (11.5361, 76.1667) to Meppadi Shelter (11.5510, 76.1280) ~4.5 km
        dist = calculate_haversine_distance(11.5361, 76.1667, 11.5510, 76.1280)
        self.assertAlmostEqual(dist, 4.5, delta=1.0)
        
        # Distance to self should be 0.0
        self.assertEqual(calculate_haversine_distance(11.5361, 76.1667, 11.5361, 76.1667), 0.0)

    def test_05_get_users_in_radius(self):
        """Verify user spatial queries and distance sorting."""
        conn = get_db_connection(self.temp_db_path)
        cursor = conn.cursor()
        
        # Insert test users at various distances from Chooralmala (11.5361, 76.1667)
        # User 1: ~1.5 km away in Mundakkai (11.5167, 76.1500)
        # User 2: ~4.5 km away in Meppadi (11.5510, 76.1280)
        # User 3: ~180 km away in Munnar, Idukki (10.0889, 77.0595)
        cursor.execute("""
            INSERT INTO users (name, phone, password_hash, lat, lng, district, role, credibility_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("Volunteer Rahul", "+919876543210", hash_password("pass1"), 11.5167, 76.1500, "Wayanad", "Volunteer", 75))
        
        cursor.execute("""
            INSERT INTO users (name, phone, password_hash, lat, lng, district, role, credibility_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("Citizen Anjali", "+919876543211", hash_password("pass2"), 11.5510, 76.1280, "Wayanad", "Citizen", 60))
        
        cursor.execute("""
            INSERT INTO users (name, phone, password_hash, lat, lng, district, role, credibility_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("Volunteer Joji", "+919876543212", hash_password("pass3"), 10.0889, 77.0595, "Idukki", "Volunteer", 80))
        conn.commit()
        conn.close()
        
        # Query 10 km radius around Chooralmala (11.5361, 76.1667)
        nearby_users = get_users_in_radius(11.5361, 76.1667, radius_km=10.0, db_path=self.temp_db_path)
        
        # Should contain Admin (at Chooralmala), Rahul, and Anjali, but NOT Joji in Idukki
        user_names = [u["name"] for u in nearby_users]
        self.assertIn("Volunteer Rahul", user_names)
        self.assertIn("Citizen Anjali", user_names)
        self.assertNotIn("Volunteer Joji", user_names)
        
        # Verify distance ordering (closest first)
        distances = [u["distance_km"] for u in nearby_users]
        self.assertEqual(distances, sorted(distances))
        
        # Verify password_hash is not leaked
        for u in nearby_users:
            self.assertNotIn("password_hash", u)

    def test_06_incident_reporting_and_spatial_query(self):
        """Verify incident reports insertion and spatial proximity retrieval."""
        conn = get_db_connection(self.temp_db_path)
        cursor = conn.cursor()
        
        # Insert sample incident reports
        cursor.execute("""
            INSERT INTO incident_reports (user_id, hazard_type, lat, lng, description, status)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (1, "mud_crack", 11.5365, 76.1670, "Deep 50cm tension crack on tea estate slope", "verified"))
        
        cursor.execute("""
            INSERT INTO incident_reports (user_id, hazard_type, lat, lng, description, status)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (1, "stream_overflow", 11.5400, 76.1700, "Muddy torrent overflowing culvert", "pending"))
        
        cursor.execute("""
            INSERT INTO incident_reports (user_id, hazard_type, lat, lng, description, status)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (1, "rockfall", 10.0889, 77.0595, "Gap road rockslide blocking traffic", "verified"))
        conn.commit()
        conn.close()
        
        # Query 5 km radius around Chooralmala
        local_incidents = get_nearby_incidents(11.5361, 76.1667, radius_km=5.0, db_path=self.temp_db_path)
        self.assertEqual(len(local_incidents), 2)
        
        # Query verified only
        verified_incidents = get_nearby_incidents(11.5361, 76.1667, radius_km=5.0, status="verified", db_path=self.temp_db_path)
        self.assertEqual(len(verified_incidents), 1)
        self.assertEqual(verified_incidents[0]["hazard_type"], "mud_crack")
        self.assertEqual(verified_incidents[0]["status"], "verified")

    def test_07_shelter_spatial_and_capacity_query(self):
        """Verify shelter querying with calculated available capacity."""
        shelters = get_nearby_shelters(11.5361, 76.1667, radius_km=20.0, district="Wayanad", db_path=self.temp_db_path)
        self.assertGreater(len(shelters), 0)
        
        for s in shelters:
            self.assertEqual(s["district"], "Wayanad")
            self.assertIn("distance_km", s)
            self.assertIn("available_capacity", s)
            self.assertEqual(s["available_capacity"], s["capacity"] - s["occupied"])
            self.assertIn("occupancy_rate_pct", s)

    def test_08_audit_logging_helper(self):
        """Verify audit log helper records actions with timestamps."""
        log_id = log_audit_action(
            action="CREDIBILITY_SCORE_UPDATED",
            actor_id=1,
            target_id=2,
            details="Credibility boosted +10 for verified hazard report",
            db_path=self.temp_db_path
        )
        self.assertIsInstance(log_id, int)
        
        conn = get_db_connection(self.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE id = ?;", (log_id,))
        log_row = cursor.fetchone()
        
        self.assertIsNotNone(log_row)
        self.assertEqual(log_row["action"], "CREDIBILITY_SCORE_UPDATED")
        self.assertEqual(log_row["actor_id"], 1)
        self.assertEqual(log_row["target_id"], 2)
        conn.close()

    def test_09_server_health_and_prediction_endpoints(self):
        """Verify server endpoints (health, hotspots, forecast, predict, shelters) operate seamlessly."""
        # 1. Health endpoint
        res = self.app.get('/api/health')
        self.assertEqual(res.status_code, 200)
        health_data = res.get_json()
        self.assertEqual(health_data["status"], "healthy")
        self.assertTrue(health_data["models"]["classifier_loaded"])
        self.assertTrue(health_data["models"]["regressor_loaded"])
        
        # 2. Hotspots endpoint
        res = self.app.get('/api/hotspots')
        self.assertEqual(res.status_code, 200)
        hotspots = res.get_json()
        self.assertIsInstance(hotspots, list)
        self.assertGreater(len(hotspots), 0)
        
        # 3. Shelters endpoint
        res = self.app.get('/api/shelters?lat=11.5361&lng=76.1667&radius_km=30')
        self.assertEqual(res.status_code, 200)
        shelters_data = res.get_json()
        self.assertTrue(shelters_data["success"])
        self.assertGreater(shelters_data["count"], 0)
        
        # 4. Predict endpoint simulation mode
        predict_payload = {
            "lat": 11.5361,
            "lng": 76.1667,
            "slope": 38.5,
            "elevation": 950,
            "soil": 1,
            "sim_mode": True,
            "manual_rainfall": 220,
            "manual_saturation": 85
        }
        res = self.app.post('/api/predict', json=predict_payload)
        self.assertEqual(res.status_code, 200)
        pred_data = res.get_json()
        self.assertIn("risk_percentage", pred_data)
        self.assertIn("live_rainfall", pred_data)
        self.assertGreaterEqual(pred_data["risk_percentage"], 0.0)


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING TERRARISK AI PHASE 1 DATABASE VERIFICATION SUITE")
    print("=" * 65)
    unittest.main(verbosity=2)
