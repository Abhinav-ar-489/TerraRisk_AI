"""
TerraRisk AI - Phase 2 Verification Suite
Tests JWT Authentication, User Registration, Login, Profile Retrieval, and Citizen Safety Check.
"""

import os
import sys
import time
import random
import unittest

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
    get_user_by_phone,
    get_user_by_id,
    create_user,
    hash_password,
    verify_password
)
from server import app, generate_jwt_token, verify_jwt_token


class TestPhase2AuthAndProfile(unittest.TestCase):
    def setUp(self):
        """Create an isolated test client with unique run identifier."""
        self.app = app.test_client()
        self.unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

    def test_01_user_registration_success(self):
        """Verify new Citizen registration returns 201, JWT token, and profile."""
        phone = f"+9198{random.randint(10000000, 99999999)}"
        payload = {
            "name": f"Citizen Test {self.unique_id}",
            "phone": phone,
            "password": "SecurePassword123!",
            "lat": 11.5510,
            "lng": 76.1280,
            "district": "Wayanad",
            "role": "Citizen"
        }
        res = self.app.post('/api/auth/register', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["name"], payload["name"])
        self.assertEqual(data["user"]["role"], "Citizen")
        self.assertEqual(data["user"]["credibility_score"], 50)
        self.assertNotIn("password_hash", data["user"])

        # Verify token validity
        decoded = verify_jwt_token(data["token"])
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["user_id"], data["user"]["id"])

    def test_02_registration_validation_and_duplicate_phone(self):
        """Verify registration rejects duplicate phone numbers and missing fields."""
        # 1. Missing fields
        res = self.app.post('/api/auth/register', json={"name": "Incomplete"})
        self.assertEqual(res.status_code, 400)

        # 2. Short password
        res = self.app.post('/api/auth/register', json={"name": "Test", "phone": "+919000000001", "password": "123"})
        self.assertEqual(res.status_code, 400)

        # 3. Duplicate phone (Authority Admin is already seeded with +919999900000)
        duplicate_payload = {
            "name": "Imposter",
            "phone": "+919999900000",
            "password": "Password123!"
        }
        res = self.app.post('/api/auth/register', json=duplicate_payload)
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_03_login_flow(self):
        """Verify login with valid credentials and rejection of invalid credentials."""
        # 1. Seed Authority Admin Login
        login_payload = {
            "phone": "+919999900000",
            "password": "Admin@Terra2026!"
        }
        res = self.app.post('/api/auth/login', json=login_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)
        self.assertEqual(data["user"]["role"], "Authority_Admin")
        self.assertEqual(data["user"]["credibility_score"], 100)

        # 2. Invalid password
        bad_payload = {
            "phone": "+919999900000",
            "password": "IncorrectPassword!"
        }
        res = self.app.post('/api/auth/login', json=bad_payload)
        self.assertEqual(res.status_code, 401)

        # 3. Non-existent phone
        unknown_payload = {
            "phone": "+910000000000",
            "password": "SomePassword!"
        }
        res = self.app.post('/api/auth/login', json=unknown_payload)
        self.assertEqual(res.status_code, 401)

    def test_04_auth_me_protected_endpoint(self):
        """Verify /api/auth/me returns the profile for authorized requests."""
        # 1. Login to get token
        login_res = self.app.post('/api/auth/login', json={
            "phone": "+919999900000",
            "password": "Admin@Terra2026!"
        })
        token = login_res.get_json()["token"]

        # 2. Authorized request
        res = self.app.get('/api/auth/me', headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "Authority_Admin")
        self.assertEqual(data["user"]["credibility_score"], 100)

        # 3. Unauthorized request (no token)
        res_no_token = self.app.get('/api/auth/me')
        self.assertEqual(res_no_token.status_code, 401)

        # 4. Unauthorized request (malformed token)
        res_bad_token = self.app.get('/api/auth/me', headers={"Authorization": "Bearer invalid.jwt.token"})
        self.assertEqual(res_bad_token.status_code, 401)

    def test_05_check_safety_endpoint(self):
        """Verify /api/user/check-safety evaluates local risk, nearest shelter, and returns safety banner status."""
        # 1. Login to obtain token
        login_res = self.app.post('/api/auth/login', json={
            "phone": "+919999900000",
            "password": "Admin@Terra2026!"
        })
        token = login_res.get_json()["token"]

        # 2. Query safety for Wayanad coordinates (Chooralmala 11.5361, 76.1667)
        res = self.app.get('/api/user/check-safety?lat=11.5361&lng=76.1667', headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn(data["status"], ["Safe", "Advisory", "Critical"])
        self.assertIn("risk_percentage", data)
        self.assertIn("live_rainfall", data)
        self.assertIn("advisory", data)
        self.assertIsNotNone(data["nearest_shelter"])
        self.assertIn("distance_km", data["nearest_shelter"])
        self.assertIn("available_capacity", data["nearest_shelter"])

    def test_06_email_verification_and_dual_login(self):
        """Verify full production flow: Registration with email/location, OTP verification, and dual login."""
        unique_num = random.randint(100000, 999999)
        test_phone = f"+919447{unique_num}"
        test_email = f"citizen_{unique_num}@kerala.gov.in"
        password = "ProductionPassword2026!"

        # 1. Register profile
        res_reg = self.app.post('/api/auth/register', json={
            "name": f"Citizen {unique_num}",
            "phone": test_phone,
            "email": test_email,
            "password": password,
            "district": "Wayanad",
            "lat": 11.5542,
            "lng": 76.1308,
            "role": "Citizen"
        })
        self.assertEqual(res_reg.status_code, 201)
        reg_data = res_reg.get_json()
        self.assertTrue(reg_data["success"])
        self.assertEqual(reg_data["step"], "verify_email")
        self.assertIn("dev_otp", reg_data)
        otp = reg_data["dev_otp"]
        self.assertEqual(len(otp), 6)

        # 2. Reject incorrect OTP code
        res_bad_otp = self.app.post('/api/auth/verify-email', json={
            "email": test_email,
            "code": "000000"
        })
        self.assertEqual(res_bad_otp.status_code, 400)

        # 3. Verify with correct OTP
        res_verify = self.app.post('/api/auth/verify-email', json={
            "email": test_email,
            "code": otp
        })
        self.assertEqual(res_verify.status_code, 200)
        verify_data = res_verify.get_json()
        self.assertTrue(verify_data["success"])
        self.assertIn("token", verify_data)
        self.assertEqual(verify_data["user"]["is_email_verified"], 1)

        # 4. Dual Login via Mobile Phone
        res_login_phone = self.app.post('/api/auth/login', json={
            "identifier": test_phone,
            "password": password
        })
        self.assertEqual(res_login_phone.status_code, 200)
        self.assertEqual(res_login_phone.get_json()["user"]["phone"], test_phone)

        # 5. Dual Login via Email Address
        res_login_email = self.app.post('/api/auth/login', json={
            "identifier": test_email,
            "password": password
        })
        self.assertEqual(res_login_email.status_code, 200)
        self.assertEqual(res_login_email.get_json()["user"]["email"], test_email)


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING TERRARISK AI PHASE 2 AUTH & PROFILE VERIFICATION SUITE")
    print("=" * 65)
    unittest.main(verbosity=2)
