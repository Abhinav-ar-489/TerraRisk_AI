"""
TerraRisk AI - Phase 4 Verification Suite
Tests Authority Triage Dashboard Endpoints, Role Access Control,
Incident Verification (+10 Credibility Reward), and Incident Rejection (-25 Credibility Penalty).
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
    get_user_by_id,
    hash_password,
    create_incident_report,
    get_pending_incident_clusters,
    verify_incident_cluster,
    reject_incident_cluster,
    get_authority_metrics
)
from server import app, generate_jwt_token


class TestPhase4AuthorityTriageAndCredibility(unittest.TestCase):
    def setUp(self):
        """Set up test client, create Authority Admin, Volunteer, and Citizen test users."""
        self.app = app.test_client()
        self.unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

        # 1. Authority Admin
        admin_phone = f"+9199{random.randint(10000000, 99999999)}"
        self.admin_id = create_user(
            name=f"Admin Commander {self.unique_id}",
            phone=admin_phone,
            password_hash=hash_password("AdminPass123!"),
            district="State Disaster Control Room",
            role="Authority_Admin",
            credibility_score=100
        )
        self.admin_token = generate_jwt_token({"id": self.admin_id, "phone": admin_phone, "role": "Authority_Admin"})

        # 2. Volunteer First Responder
        vol_phone = f"+9197{random.randint(10000000, 99999999)}"
        self.vol_id = create_user(
            name=f"Volunteer Responser {self.unique_id}",
            phone=vol_phone,
            password_hash=hash_password("VolPass123!"),
            district="Wayanad",
            role="Volunteer",
            credibility_score=80
        )
        self.vol_token = generate_jwt_token({"id": self.vol_id, "phone": vol_phone, "role": "Volunteer"})

        # 3. Standard Citizen (Credibility = 50)
        cit_phone = f"+9198{random.randint(10000000, 99999999)}"
        self.cit_id = create_user(
            name=f"Citizen Test {self.unique_id}",
            phone=cit_phone,
            password_hash=hash_password("CitPass123!"),
            district="Idukki",
            role="Citizen",
            credibility_score=50
        )
        self.citizen_token = generate_jwt_token({"id": self.cit_id, "phone": cit_phone, "role": "Citizen"})

    def test_01_citizen_role_forbidden_from_authority_routes(self):
        """Verify standard Citizen is blocked (403 Forbidden) from authority triage endpoints."""
        # 1. Pending clusters
        res = self.app.get('/api/authority/pending-clusters', headers={"Authorization": f"Bearer {self.citizen_token}"})
        self.assertEqual(res.status_code, 403)
        self.assertFalse(res.get_json()["success"])
        self.assertIn("Access restricted", res.get_json()["error"])

        # 2. Metrics
        res = self.app.get('/api/authority/metrics', headers={"Authorization": f"Bearer {self.citizen_token}"})
        self.assertEqual(res.status_code, 403)

        # 3. Verify action
        res = self.app.post('/api/incidents/verify', json={"cluster_id": "test"}, headers={"Authorization": f"Bearer {self.citizen_token}"})
        self.assertEqual(res.status_code, 403)

        # 4. Reject action
        res = self.app.post('/api/incidents/reject', json={"cluster_id": "test"}, headers={"Authorization": f"Bearer {self.citizen_token}"})
        self.assertEqual(res.status_code, 403)

    def test_02_authority_and_volunteer_can_access_triage_and_metrics(self):
        """Verify Authority Admin and Volunteer successfully retrieve triage queue and metrics."""
        # Admin access
        res_admin = self.app.get('/api/authority/pending-clusters', headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_admin.status_code, 200)
        data_admin = res_admin.get_json()
        self.assertTrue(data_admin["success"])
        self.assertIsInstance(data_admin["clusters"], list)

        # Volunteer access
        res_vol = self.app.get('/api/authority/pending-clusters', headers={"Authorization": f"Bearer {self.vol_token}"})
        self.assertEqual(res_vol.status_code, 200)

        # Metrics
        res_metrics = self.app.get('/api/authority/metrics', headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_metrics.status_code, 200)
        metrics = res_metrics.get_json()["metrics"]
        self.assertIn("total_pending_reports", metrics)
        self.assertIn("active_verified_hazards", metrics)
        self.assertIn("active_field_volunteers", metrics)

    def test_03_verify_cluster_rewards_citizen_credibility(self):
        """Verify incident verification updates status to 'verified' and adds +10 to citizen credibility."""
        test_cluster_id = f"clust_ver_{self.unique_id}"
        
        # Create pending incident report by citizen (credibility = 50)
        rep_id = create_incident_report(
            user_id=self.cit_id,
            hazard_type="rockfall",
            lat=11.5540,
            lng=76.1310,
            description="Massive boulder on roadside",
            severity=4,
            cluster_id=test_cluster_id,
            status="pending"
        )

        # Authority Admin verifies cluster
        res = self.app.post(
            '/api/incidents/verify',
            json={"cluster_id": test_cluster_id},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["verified_reports_count"], 1)

        # Check citizen's updated credibility score (50 -> 60)
        updated_cit = get_user_by_id(self.cit_id)
        self.assertEqual(updated_cit["credibility_score"], 60)

    def test_04_reject_cluster_penalizes_citizen_credibility(self):
        """Verify incident rejection updates status to 'rejected' and deducts -25 from citizen credibility."""
        test_cluster_id = f"clust_rej_{self.unique_id}"
        
        # Create pending incident report by citizen (credibility = 50)
        rep_id = create_incident_report(
            user_id=self.cit_id,
            hazard_type="stream_overflow",
            lat=11.5580,
            lng=76.1350,
            description="Fabricated overflow alert",
            severity=3,
            cluster_id=test_cluster_id,
            status="pending"
        )

        # Authority Admin rejects cluster as spam
        res = self.app.post(
            '/api/incidents/reject',
            json={"cluster_id": test_cluster_id, "reason": "Spam / Fabricated"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["rejected_reports_count"], 1)

        # Check citizen's updated credibility score (50 -> 25)
        updated_cit = get_user_by_id(self.cit_id)
        self.assertEqual(updated_cit["credibility_score"], 25)

    def test_05_credibility_clamping_boundaries(self):
        """Verify credibility score is clamped at max 100 on reward and min 0 on penalty."""
        # 1. High Credibility Citizen (95) -> Reward +10 => should clamp to 100
        phone_high = f"+9198{random.randint(10000000, 99999999)}"
        u_high_id = create_user("High Cred User", phone_high, hash_password("Pass1!"), district="Wayanad", role="Citizen", credibility_score=95)
        c_high = f"clust_high_{self.unique_id}"
        create_incident_report(u_high_id, "mud_crack", 11.60, 76.14, "Crack", 3, cluster_id=c_high, status="pending")

        verify_incident_cluster(c_high, verified_by_user_id=self.admin_id)
        self.assertEqual(get_user_by_id(u_high_id)["credibility_score"], 100)

        # 2. Low Credibility Citizen (15) -> Penalty -25 => should clamp to 0 (not negative)
        phone_low = f"+9198{random.randint(10000000, 99999999)}"
        u_low_id = create_user("Low Cred User", phone_low, hash_password("Pass1!"), district="Wayanad", role="Citizen", credibility_score=15)
        c_low = f"clust_low_{self.unique_id}"
        create_incident_report(u_low_id, "slope_movement", 11.62, 76.15, "Creep", 2, cluster_id=c_low, status="pending")

        reject_incident_cluster(c_low, rejected_by_user_id=self.admin_id, reason="Resolved / Non-Threat")
        self.assertEqual(get_user_by_id(u_low_id)["credibility_score"], 0)


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING TERRARISK AI PHASE 4 AUTHORITY TRIAGE & CREDIBILITY SUITE")
    print("=" * 65)
    unittest.main(verbosity=2)
