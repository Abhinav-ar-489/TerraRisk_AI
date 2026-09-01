"""
TerraRisk AI - Phase 5 Verification Suite
Tests Bilingual LLM Alert Synthesis (Ollama LLaMA 3.2), Spatial Geofenced SMS Dispatch,
OASIS/NDMA CAP v1.2 XML Feed, and CAP JSON APIs.
"""

import os
import sys
import time
import random
import unittest
import xml.etree.ElementTree as ET

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
    create_user,
    hash_password,
    create_incident_report
)
from alerts import (
    synthesize_bilingual_alert,
    dispatch_geofenced_sms,
    get_active_broadcasts,
    generate_cap_xml,
    generate_cap_json
)
from server import app, generate_jwt_token


class TestPhase5GeofencedAlertingAndCAP(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

        # 1. Authority Admin
        admin_phone = f"+9199{random.randint(10000000, 99999999)}"
        self.admin_id = create_user(
            name=f"Commander Admin {self.unique_id}",
            phone=admin_phone,
            password_hash=hash_password("AdminPass123!"),
            district="State Disaster Control Room",
            role="Authority_Admin",
            credibility_score=100
        )
        self.admin_token = generate_jwt_token({"id": self.admin_id, "phone": admin_phone, "role": "Authority_Admin"})

        # 2. Citizen in Danger Zone (1.2 km away)
        self.hazard_lat = 11.5542
        self.hazard_lng = 76.1308

        cit_near_phone = f"+9198{random.randint(10000000, 99999999)}"
        self.cit_near_id = create_user(
            name=f"Near Citizen {self.unique_id}",
            phone=cit_near_phone,
            password_hash=hash_password("Pass123!"),
            lat=self.hazard_lat + 0.008,
            lng=self.hazard_lng + 0.006,
            district="Wayanad",
            role="Citizen",
            credibility_score=50
        )

        # 3. Citizen Far Outside Danger Zone (35 km away)
        cit_far_phone = f"+9198{random.randint(10000000, 99999999)}"
        self.cit_far_id = create_user(
            name=f"Far Citizen {self.unique_id}",
            phone=cit_far_phone,
            password_hash=hash_password("Pass123!"),
            lat=self.hazard_lat + 0.35,
            lng=self.hazard_lng + 0.35,
            district="Kozhikode",
            role="Citizen",
            credibility_score=50
        )
        self.citizen_token = generate_jwt_token({"id": self.cit_far_id, "phone": cit_far_phone, "role": "Citizen"})

    def test_01_bilingual_synthesis_returns_en_and_ml(self):
        """Verify bilingual synthesis generates both English and Malayalam emergency warnings."""
        res = synthesize_bilingual_alert(
            hazard_type="slope_movement",
            location_name="Meppadi Sector, Wayanad",
            severity=5,
            radius_km=5.0
        )
        self.assertIn("alert_en", res)
        self.assertIn("alert_ml", res)
        self.assertGreater(len(res["alert_en"]), 20)
        self.assertGreater(len(res["alert_ml"]), 20)
        # Check Malayalam script characters
        self.assertTrue(any('\u0D00' <= char <= '\u0D7F' for char in res["alert_ml"]))

    def test_02_spatial_dispatch_isolates_geofenced_users(self):
        """Verify geofenced dispatch only targets users inside radius (ignores distant users)."""
        result = dispatch_geofenced_sms(
            lat=self.hazard_lat,
            lng=self.hazard_lng,
            radius_km=5.0,
            alert_en="EVACUATE: Danger zone alert",
            alert_ml="അടിയന്തര മുന്നറിയിപ്പ്",
            hazard_type="rockfall"
        )
        self.assertTrue(result["success"])
        self.assertIn("broadcast_id", result)
        
        # Check recipient IDs
        delivered_user_ids = [d["user_id"] for d in result["delivered"]]
        self.assertIn(self.cit_near_id, delivered_user_ids)
        self.assertNotIn(self.cit_far_id, delivered_user_ids)

    def test_03_preview_endpoint_and_role_protection(self):
        """Verify /api/alerts/preview returns bilingual drafts and citizen count for Authority, 403 for Citizen."""
        # Authority Preview
        res_admin = self.app.post(
            '/api/alerts/preview',
            json={
                "lat": self.hazard_lat,
                "lng": self.hazard_lng,
                "radius_km": 5.0,
                "hazard_type": "stream_overflow",
                "severity": 4
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res_admin.status_code, 200)
        data = res_admin.get_json()
        self.assertTrue(data["success"])
        self.assertIn("alert_en", data)
        self.assertIn("alert_ml", data)
        self.assertGreaterEqual(data["target_citizens_count"], 1)

        # Citizen Blocked
        res_cit = self.app.post(
            '/api/alerts/preview',
            json={"lat": self.hazard_lat, "lng": self.hazard_lng, "radius_km": 5.0},
            headers={"Authorization": f"Bearer {self.citizen_token}"}
        )
        self.assertEqual(res_cit.status_code, 403)

    def test_04_broadcast_endpoint_and_active_broadcasts(self):
        """Verify /api/alerts/broadcast triggers geofenced broadcast and updates /api/alerts/active-broadcasts."""
        res = self.app.post(
            '/api/alerts/broadcast',
            json={
                "lat": self.hazard_lat,
                "lng": self.hazard_lng,
                "radius_km": 6.0,
                "hazard_type": "slope_movement",
                "alert_en": "Critical evacuation order for Meppadi slope",
                "alert_ml": "മേപ്പാടി പ്രദേശത്ത് അടിയന്തര ഒഴിപ്പിക്കൽ ഉത്തരവ്"
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        bcast_data = res.get_json()
        self.assertTrue(bcast_data["success"])
        self.assertIn("broadcast_id", bcast_data)

        # Query active broadcasts public endpoint
        res_active = self.app.get('/api/alerts/active-broadcasts')
        self.assertEqual(res_active.status_code, 200)
        active_list = res_active.get_json()["broadcasts"]
        broadcast_ids = [b["broadcast_id"] for b in active_list]
        self.assertIn(bcast_data["broadcast_id"], broadcast_ids)

    def test_05_cap_xml_feed_standard_structure(self):
        """Verify /api/alerts/cap.xml produces valid ITU-T / OASIS CAP v1.2 XML markup."""
        res = self.app.get('/api/alerts/cap.xml')
        self.assertEqual(res.status_code, 200)
        self.assertIn('application/xml', res.headers.get('Content-Type', ''))
        
        xml_str = res.get_data(as_text=True)
        self.assertIn("<alert", xml_str)
        self.assertIn("urn:oasis:names:tc:emergency:cap:1.2", xml_str)
        self.assertIn("<identifier>", xml_str)
        self.assertIn("<info>", xml_str)
        self.assertIn("<language>en-IN</language>", xml_str)
        self.assertIn("<language>ml-IN</language>", xml_str)

        # Parse XML tree to verify well-formedness
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_06_cap_json_feed_structure(self):
        """Verify /api/alerts/cap.json returns valid CAP JSON structure with bilingual alerts."""
        res = self.app.get('/api/alerts/cap.json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["cap_version"], "1.2")
        self.assertIn("sender", data)
        self.assertIn("alerts", data)
        self.assertIsInstance(data["alerts"], list)


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING TERRARISK AI PHASE 5 GEOFENCED ALERT & CAP v1.2 SUITE")
    print("=" * 65)
    unittest.main(verbosity=2)
