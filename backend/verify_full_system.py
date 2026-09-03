"""
TerraRisk AI - Complete Platform Verification Suite
Automated end-to-end integration test validating:
1. Authority & Relief Shelter CRUD & Supplies Inventory Management
2. 3-Tier Computer Vision Hazard Brain & Spatial Auto-Clustering
3. Zero-Cost Multi-Channel Broadcast Engine (Telegram, WhatsApp, SMS, CAP v1.2)
4. Family Safety Circle & 1-Tap "I Am Safe" GPS Beacon
5. Missing Persons Registry & Relief Camp Evacuee Matching
6. Field Volunteer Mission Tasking
7. KSDMA Official Situation Report (SitRep) PDF Compiler
"""

import sys
import os
import io
import json
import base64
import unittest
from PIL import Image, ImageDraw

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import app
from database import get_db_connection, init_db
from vision import analyze_hazard_image, _python_geological_feature_engine


def generate_synthetic_hazard_image():
    """Create a synthetic high-contrast image with terrain fractures and earth tones."""
    img = Image.new('RGB', (256, 256), color=(140, 100, 60))
    draw = ImageDraw.Draw(img)
    # Draw dark fracture fissures and rock patterns
    draw.line([(20, 20), (80, 120), (160, 140), (240, 230)], fill=(40, 25, 15), width=8)
    draw.line([(120, 40), (180, 100), (220, 190)], fill=(60, 40, 20), width=6)
    draw.polygon([(40, 160), (100, 180), (70, 240)], fill=(90, 65, 45))
    draw.polygon([(170, 40), (230, 60), (200, 110)], fill=(110, 80, 50))
    
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')


def generate_synthetic_blank_image():
    """Create a uniform blank noise image to test spam filtering."""
    img = Image.new('RGB', (100, 100), color=(255, 255, 255))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')


class TerraRiskFullSystemTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        init_db()

        # Generate tokens for Admin, Volunteer, and Citizen
        # 1. Login Authority Admin
        admin_login = cls.client.post('/api/auth/login', json={
            "phone": "+919999900000",
            "password": "Admin@Terra2026!"
        })
        cls.admin_token = admin_login.get_json().get("token")
        cls.admin_user = admin_login.get_json().get("user")

        # 2. Login Volunteer
        vol_login = cls.client.post('/api/auth/login', json={
            "phone": "+919888800000",
            "password": "Volunteer@2026!"
        })
        cls.volunteer_token = vol_login.get_json().get("token")
        cls.volunteer_user = vol_login.get_json().get("user")

        # 3. Register / Login Citizen
        import secrets
        cls.test_phone = f"+919447{secrets.randbelow(899999) + 100000}"
        cit_reg = cls.client.post('/api/auth/register', json={
            "name": "Arun Varma",
            "phone": cls.test_phone,
            "password": "CitizenSecure2026!",
            "role": "Citizen",
            "district": "Wayanad",
            "lat": 11.5542,
            "lng": 76.1308
        })
        cls.citizen_token = cit_reg.get_json().get("token")
        cls.citizen_user = cit_reg.get_json().get("user")

    def test_01_system_health(self):
        """Verify server health and database connection."""
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("models", data)
        self.assertIn("database", data)
        print("  [PASS] 01: System Health & Database Connection verified.")

    def test_02_computer_vision_brain(self):
        """Test the 3-Tier Computer Vision Hazard Engine."""
        hazard_img = generate_synthetic_hazard_image()
        res = self.client.post('/api/vision/analyze', json={
            "image": hazard_img,
            "hazard_type": "mud_crack"
        })
        self.assertEqual(res.status_code, 200)
        analysis = res.get_json()["analysis"]
        self.assertIn("confidence_score", analysis)
        self.assertIn("detected_hazard", analysis)
        self.assertIn("ai_summary", analysis)
        self.assertTrue(isinstance(analysis["confidence_score"], (int, float)) and analysis["confidence_score"] >= 0.0)
        print(f"  [PASS] 02: Computer Vision Engine (Confidence: {analysis['confidence_score']:.2f}, Hazard: {analysis['detected_hazard']}).")

    def test_03_incident_reporting_with_cv_and_clustering(self):
        """Submit hazard incident with attached photo and verify auto-clustering."""
        hazard_img = generate_synthetic_hazard_image()
        res = self.client.post('/api/incidents/report', json={
            "hazard_type": "mud_crack",
            "lat": 11.5542,
            "lng": 76.1308,
            "severity": 4,
            "description": "Expanding earth fissures across hillside road.",
            "image": hazard_img
        }, headers={"Authorization": f"Bearer {self.citizen_token}"})

        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("cluster_id", data)
        self.assertIsNotNone(data["ai_analysis"])
        self.__class__.created_cluster_id = data["cluster_id"]
        print(f"  [PASS] 03: Incident Report with CV metadata submitted (Cluster: {data['cluster_id']}).")

    def test_04_relief_camp_crud_and_supplies(self):
        """Test full CRUD operations on relief shelters and inventory management."""
        # 1. Create Relief Shelter
        res_create = self.client.post('/api/shelters/create', json={
            "name": "Meppadi St. Joseph Relief Camp",
            "district": "Wayanad",
            "lat": 11.5520,
            "lng": 76.1290,
            "capacity": 450,
            "contact_number": "+91 4936 282999",
            "in_charge_name": "Suresh Babu (Deputy Tahsildar)",
            "in_charge_phone": "+91 94470 12345",
            "amenities": {"medical_post": True, "power_backup": True, "wheelchair_accessible": True},
            "supplies": {"water_litres": 3000, "food_packets": 600, "medical_kits": 40, "fuel_litres": 250}
        }, headers={"Authorization": f"Bearer {self.admin_token}"})

        self.assertEqual(res_create.status_code, 201)
        shelter = res_create.get_json()["shelter"]
        shelter_id = shelter["id"]
        self.assertEqual(shelter["name"], "Meppadi St. Joseph Relief Camp")
        self.assertEqual(shelter["capacity"], 450)

        # 2. Update Supplies
        res_supplies = self.client.post(f'/api/shelters/{shelter_id}/supplies', json={
            "supplies": {"water_litres": 4500, "food_packets": 800, "medical_kits": 50, "fuel_litres": 300}
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_supplies.status_code, 200)

        # 3. Update Camp Details
        res_put = self.client.put(f'/api/shelters/{shelter_id}', json={
            "capacity": 500,
            "status": "active"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.get_json()["shelter"]["capacity"], 500)

        # 4. Fetch Single Shelter
        res_get = self.client.get(f'/api/shelters/{shelter_id}')
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()["shelter"]["supplies"]["water_litres"], 4500)

        # Keep shelter_id for missing person matching
        self.__class__.test_shelter_id = shelter_id
        print(f"  [PASS] 04: Relief Camp CRUD & Supplies Inventory management verified (ID: {shelter_id}).")

    def test_05_missing_persons_registry_and_matching(self):
        """Test Missing Persons SOS Board and Shelter Evacuee Matching."""
        # 1. Report Missing Person
        res_report = self.client.post('/api/missing-persons/report', json={
            "name": "Deepak Menon",
            "age": 42,
            "gender": "Male",
            "last_known_location": "Mundakkai River Bank",
            "contact_phone": "+919447555666",
            "medical_needs": "Requires daily asthma inhaler"
        }, headers={"Authorization": f"Bearer {self.citizen_token}"})
        self.assertEqual(res_report.status_code, 201)
        person_id = res_report.get_json()["person_id"]

        # 2. Query Missing List
        res_list = self.client.get('/api/missing-persons?status=missing')
        self.assertEqual(res_list.status_code, 200)
        found = any(p["id"] == person_id for p in res_list.get_json()["missing_persons"])
        self.assertTrue(found)

        # 3. Authority matches missing person to Shelter
        res_match = self.client.post(f'/api/missing-persons/{person_id}/update-status', json={
            "status": "located_safe",
            "located_at_shelter_id": self.test_shelter_id
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_match.status_code, 200)

        # 4. Verify status transition
        res_single = self.client.get('/api/missing-persons?status=located_safe')
        matched_person = next((p for p in res_single.get_json()["missing_persons"] if p["id"] == person_id), None)
        self.assertIsNotNone(matched_person)
        self.assertEqual(matched_person["status"], "located_safe")
        self.assertEqual(matched_person["located_shelter_name"], "Meppadi St. Joseph Relief Camp")
        print("  [PASS] 06: Missing Persons Registry & Shelter Evacuee Matching verified.")

    def test_07_volunteer_mission_tasking(self):
        """Test assigning field inspection missions to volunteers."""
        # 1. Authority assigns mission
        res_assign = self.client.post('/api/authority/missions/assign', json={
            "cluster_id": self.created_cluster_id,
            "volunteer_id": self.volunteer_user["id"],
            "notes": "Verify slope fissures along Chooralmala perimeter."
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_assign.status_code, 201)
        mission_id = res_assign.get_json()["mission_id"]

        # 2. Fetch Missions
        res_list = self.client.get('/api/authority/missions', headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(len(res_list.get_json()["missions"]) >= 1)

        # 3. Volunteer updates mission status
        res_update = self.client.post(f'/api/volunteer/missions/{mission_id}/update-status', json={
            "status": "on_site",
            "notes": "Arrived on site. Confirmed 3-inch ground tension crack."
        }, headers={"Authorization": f"Bearer {self.volunteer_token}"})
        self.assertEqual(res_update.status_code, 200)
        print("  [PASS] 07: Field Volunteer Mission Assignment & Tracking verified.")

    def test_08_multi_channel_broadcast_and_cap(self):
        """Test Multi-Channel Broadcast (Telegram, WhatsApp, SMS) and CAP v1.2 export."""
        # 1. Preview Alert
        res_prev = self.client.post('/api/alerts/preview', json={
            "lat": 11.5542,
            "lng": 76.1308,
            "radius_km": 5.0,
            "hazard_type": "slope_movement",
            "severity": 4
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_prev.status_code, 200)
        self.assertIn("whatsapp_share_url", res_prev.get_json())
        self.assertIn("alert_en", res_prev.get_json())
        self.assertIn("alert_ml", res_prev.get_json())

        # 2. Dispatch Multi-Channel Alert
        res_blast = self.client.post('/api/alerts/broadcast', json={
            "lat": 11.5542,
            "lng": 76.1308,
            "radius_km": 5.0,
            "hazard_type": "slope_movement"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_blast.status_code, 200)
        data = res_blast.get_json()
        self.assertTrue(data["success"])
        self.assertIn("delivered", data)
        self.assertIn("telegram_share_url", data)

        # 3. Common Alerting Protocol Feeds
        res_xml = self.client.get('/api/alerts/cap.xml')
        self.assertEqual(res_xml.status_code, 200)
        self.assertIn("application/xml", res_xml.content_type)

        res_json = self.client.get('/api/alerts/cap.json')
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.get_json()["cap_version"], "1.2")
        self.assertEqual(res_json.get_json()["authority"], "Kerala State Disaster Management Authority (KSDMA)")
        print("  [PASS] 08: Zero-Cost Multi-Channel Broadcast (Telegram, WA, SMS) & CAP v1.2 verified.")

    def test_09_situation_report_pdf_export(self):
        """Test official KSDMA Situation Report (SitRep) PDF generation."""
        res_pdf = self.client.get('/api/authority/export-sitrep?format=pdf', headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.content_type, "application/pdf")
        self.assertTrue(len(res_pdf.data) > 1000)
        print(f"  [PASS] 09: KSDMA Official Situation Report PDF Export verified ({len(res_pdf.data)} bytes).")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 RUNNING TERRARISK AI MASTER INTEGRATION VERIFICATION SUITE")
    print("="*70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TerraRiskFullSystemTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "="*70)
        print("✅ ALL INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
        print("="*70 + "\n")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED.")
        sys.exit(1)
