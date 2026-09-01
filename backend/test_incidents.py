"""
TerraRisk AI - Phase 3 Verification Suite
Tests Citizen Incident Reporting, Credibility Spam Prevention, 500m Spatial Auto-Clustering, and Active Incident Aggregation.
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
    create_user,
    hash_password,
    create_incident_report,
    find_nearby_pending_cluster,
    get_active_incident_clusters
)
from server import app, generate_jwt_token


class TestPhase3IncidentReportingAndClustering(unittest.TestCase):
    def setUp(self):
        """Set up test client and create authenticated users with unique test sector."""
        self.app = app.test_client()
        self.unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

        # Generate unique base coordinates for this test run to prevent collision with previous runs
        self.base_lat = 9.0000 + random.uniform(0.05, 2.50)
        self.base_lng = 76.0000 + random.uniform(0.05, 0.80)

        # 1. Standard Citizen (Credibility = 50)
        phone1 = f"+9198{random.randint(10000000, 99999999)}"
        u1_id = create_user(
            name=f"Citizen Reporter 1 {self.unique_id}",
            phone=phone1,
            password_hash=hash_password("Pass123!"),
            lat=self.base_lat,
            lng=self.base_lng,
            district="Wayanad",
            role="Citizen",
            credibility_score=50
        )
        self.user1_token = generate_jwt_token({"id": u1_id, "phone": phone1, "role": "Citizen"})

        # 2. Second Citizen (Credibility = 60)
        phone2 = f"+9198{random.randint(10000000, 99999999)}"
        u2_id = create_user(
            name=f"Citizen Reporter 2 {self.unique_id}",
            phone=phone2,
            password_hash=hash_password("Pass123!"),
            lat=self.base_lat + 0.001,
            lng=self.base_lng + 0.001,
            district="Wayanad",
            role="Citizen",
            credibility_score=60
        )
        self.user2_token = generate_jwt_token({"id": u2_id, "phone": phone2, "role": "Citizen"})

        # 3. Low-credibility / Spammer Account (Credibility = 5)
        phone3 = f"+9198{random.randint(10000000, 99999999)}"
        u3_id = create_user(
            name=f"Low Cred User {self.unique_id}",
            phone=phone3,
            password_hash=hash_password("Pass123!"),
            lat=self.base_lat,
            lng=self.base_lng,
            district="Wayanad",
            role="Citizen",
            credibility_score=5
        )
        self.low_cred_token = generate_jwt_token({"id": u3_id, "phone": phone3, "role": "Citizen"})

    def test_01_low_credibility_user_blocked(self):
        """Verify user with credibility < 10 is blocked with 403 Forbidden."""
        payload = {
            "hazard_type": "mud_crack",
            "lat": self.base_lat,
            "lng": self.base_lng,
            "description": "Fissure on slope",
            "severity": 3
        }
        res = self.app.post(
            '/api/incidents/report',
            json=payload,
            headers={"Authorization": f"Bearer {self.low_cred_token}"}
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("credibility score is below", data["error"])

    def test_02_first_incident_creates_new_cluster(self):
        """Verify initial report is assigned a new cluster ID and stored as pending."""
        lat = self.base_lat + 0.20
        lng = self.base_lng + 0.20
        payload = {
            "hazard_type": "rockfall",
            "lat": lat,
            "lng": lng,
            "description": "Boulders tumbling down Meppadi slope",
            "severity": 4
        }
        res = self.app.post(
            '/api/incidents/report',
            json=payload,
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("incident_id", data)
        self.assertIn("cluster_id", data)
        self.assertTrue(data["cluster_id"].startswith("clust_"))
        self.assertFalse(data["is_clustered"])

    def test_03_nearby_report_within_500m_auto_clusters(self):
        """Verify second report within 250m joins the existing pending cluster."""
        lat1 = self.base_lat + 0.40
        lng1 = self.base_lng + 0.40

        # Report 1
        payload1 = {
            "hazard_type": "mud_crack",
            "lat": lat1,
            "lng": lng1,
            "description": "Deep tension crack expanding",
            "severity": 3
        }
        res1 = self.app.post(
            '/api/incidents/report',
            json=payload1,
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(res1.status_code, 201)
        cluster1_id = res1.get_json()["cluster_id"]

        # Report 2 (~150 meters away)
        lat2 = lat1 + 0.0010
        lng2 = lng1 + 0.0008
        payload2 = {
            "hazard_type": "mud_crack",
            "lat": lat2,
            "lng": lng2,
            "description": "Soil sliding across driveway",
            "severity": 4
        }
        res2 = self.app.post(
            '/api/incidents/report',
            json=payload2,
            headers={"Authorization": f"Bearer {self.user2_token}"}
        )
        self.assertEqual(res2.status_code, 201)
        data2 = res2.get_json()
        self.assertTrue(data2["is_clustered"])
        self.assertEqual(data2["cluster_id"], cluster1_id)

    def test_04_distant_report_creates_separate_cluster(self):
        """Verify distant report (>500m) generates a separate distinct cluster ID."""
        lat1 = self.base_lat + 0.60
        lng1 = self.base_lng + 0.60

        res1 = self.app.post(
            '/api/incidents/report',
            json={"hazard_type": "stream_overflow", "lat": lat1, "lng": lng1, "severity": 3},
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(res1.status_code, 201)
        cluster1_id = res1.get_json()["cluster_id"]

        # Report 2 (~15 km away)
        lat2 = lat1 + 0.15
        lng2 = lng1 + 0.15
        res2 = self.app.post(
            '/api/incidents/report',
            json={"hazard_type": "rockfall", "lat": lat2, "lng": lng2, "severity": 4},
            headers={"Authorization": f"Bearer {self.user2_token}"}
        )
        self.assertEqual(res2.status_code, 201)
        cluster2_id = res2.get_json()["cluster_id"]

        self.assertNotEqual(cluster1_id, cluster2_id)
        self.assertFalse(res2.get_json()["is_clustered"])

    def test_05_active_incidents_clustering_aggregation(self):
        """Verify /api/incidents/active aggregates report count and computes average severity."""
        res = self.app.get('/api/incidents/active')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["incidents"], list)
        self.assertGreater(data["count"], 0)

        for inc in data["incidents"]:
            self.assertIn("cluster_id", inc)
            self.assertIn("primary_hazard_type", inc)
            self.assertIn("lat", inc)
            self.assertIn("lng", inc)
            self.assertIn("report_count", inc)
            self.assertIn("avg_severity", inc)
            self.assertIn("status", inc)
            self.assertGreaterEqual(inc["report_count"], 1)


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING TERRARISK AI PHASE 3 INCIDENT REPORTING & CLUSTERING SUITE")
    print("=" * 65)
    unittest.main(verbosity=2)
