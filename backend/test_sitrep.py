"""
Unit Tests for TerraRisk AI - Phase 8 Situation Report (SitRep) PDF Exporter & Telemetry Suite
"""

import os
import sys
import unittest
import json

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import (
    init_db,
    create_incident_report,
    verify_incident_cluster
)
from sitrep import (
    generate_sitrep_data,
    generate_sitrep_pdf
)
from server import app, generate_jwt_token

TEST_DB = os.path.join(os.path.dirname(__file__), "data", "test_sitrep_disaster.db")


class TestPhase8SitRepExporter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_PATH"] = TEST_DB
        init_db(db_path=TEST_DB)
        cls.app = app
        cls.client = cls.app.test_client()

        # Seed an active verified hazard
        c_id = create_incident_report(
            user_id=1,
            hazard_type="rockfall",
            lat=11.5542,
            lng=76.1308,
            description="Active rockfall across ghat hairpin corridor",
            severity=4,
            db_path=TEST_DB
        )
        verify_incident_cluster(c_id, verified_by_user_id=1, db_path=TEST_DB)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def test_01_sitrep_data_generation(self):
        """Verify SitRep telemetry compiles incident counts, threat levels, and shelter occupancies."""
        data = generate_sitrep_data(district="Wayanad", db_path=TEST_DB)
        
        self.assertIn("report_id", data)
        self.assertTrue(data["report_id"].startswith("SITREP-KSDMA-"))
        self.assertIn("threat_level", data)
        self.assertIn("metrics", data)
        self.assertIn("shelters", data)
        self.assertGreater(data["total_shelters"], 0)
        self.assertGreaterEqual(data["total_capacity"], 0)
        self.assertGreaterEqual(data["verified_count"], 1)

    def test_02_sitrep_pdf_stream_generation(self):
        """Verify ReportLab PDF compiler generates valid PDF binary stream."""
        pdf_bytes = generate_sitrep_pdf(
            district="Wayanad",
            author_name="District Collector & District Magistrate",
            db_path=TEST_DB
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        # PDF magic header signature
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_03_sitrep_api_endpoints_role_protection(self):
        """Verify /api/authority/export-sitrep enforces RBAC and delivers both JSON and PDF formats."""
        # 1. Unauthenticated Request -> 401
        unauth_res = self.client.get("/api/authority/export-sitrep")
        self.assertEqual(unauth_res.status_code, 401)

        # 2. Citizen Request -> 403 Forbidden
        citizen_user = {"id": 10, "name": "Citizen User", "phone": "+919111111111", "role": "Citizen"}
        citizen_token = generate_jwt_token(citizen_user)
        citizen_res = self.client.get(
            "/api/authority/export-sitrep",
            headers={"Authorization": f"Bearer {citizen_token}"}
        )
        self.assertEqual(citizen_res.status_code, 403)

        # 3. Authority Admin Request (JSON format) -> 200
        admin_user = {"id": 1, "name": "Collector Wayanad", "phone": "+919999999999", "role": "Authority_Admin"}
        admin_token = generate_jwt_token(admin_user)
        
        json_res = self.client.get(
            "/api/authority/export-sitrep?format=json&district=Wayanad",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(json_res.status_code, 200)
        data = json_res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("sitrep", data)

        # 4. Authority Admin Request (PDF format) -> 200 (application/pdf)
        pdf_res = self.client.get(
            "/api/authority/export-sitrep?format=pdf&district=Wayanad",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.content_type, "application/pdf")
        self.assertTrue(pdf_res.data.startswith(b"%PDF-"))
        self.assertIn("attachment; filename=", pdf_res.headers.get("Content-Disposition", ""))


if __name__ == "__main__":
    unittest.main()
