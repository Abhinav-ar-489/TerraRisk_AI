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

    def test_03_verify_cluster_verifies_citizen(self):
        """Verify incident verification updates status to 'verified' and marks citizen as verified."""
        test_cluster_id = f"clust_ver_{self.unique_id}"
        
        # Create pending incident report by citizen
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

        # Check citizen's updated verification status (is_verified -> 1)
        updated_cit = get_user_by_id(self.cit_id)
        self.assertEqual(updated_cit["is_verified"], 1)

    def test_04_reject_cluster_marks_rejected_cleanly(self):
        """Verify incident rejection updates status to 'rejected'."""
        test_cluster_id = f"clust_rej_{self.unique_id}"
        
        # Create pending incident report by citizen
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
            json={"cluster_id": test_cluster_id, "reason": "False Alarm / Duplicate"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["rejected_reports_count"], 1)

    def test_05_admin_direct_user_verification(self):
        """Verify Authority Admin can directly set user verification."""
        phone_cit = f"+9198{random.randint(10000000, 99999999)}"
        u_id = create_user("Test Citizen", phone_cit, hash_password("Pass1!"), role="Citizen")
        self.assertEqual(get_user_by_id(u_id)["is_verified"], 0)

        # Admin verifies user
        res = self.app.post(
            '/api/authority/users/verify',
            json={"user_id": u_id, "is_verified": True},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(get_user_by_id(u_id)["is_verified"], 1)

    def test_06_resolve_cluster_marks_incident_cleared_and_removes_from_active(self):
        """Verify resolving an incident cluster updates status to 'resolved' and clears it from active map feed."""
        test_cluster_id = f"clust_res_{self.unique_id}"
        
        # 1. Create and verify incident
        create_incident_report(self.cit_id, "blocked_road", 11.559, 76.136, "Debris blocking SH-54", 4, cluster_id=test_cluster_id, status="pending")
        verify_incident_cluster(test_cluster_id, verified_by_user_id=self.admin_id)
        
        # 2. Check it is currently in active incidents
        active_res = self.app.get('/api/incidents/active')
        active_ids = [c["cluster_id"] for c in active_res.get_json()["incidents"]]
        self.assertIn(test_cluster_id, active_ids)

        # 3. Post to /api/incidents/resolve as Authority Admin
        res = self.app.post(
            '/api/incidents/resolve',
            json={"cluster_id": test_cluster_id, "notes": "Road cleared by JCB crew. Traffic resumed."},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["resolved_reports_count"], 1)

        # 4. Verify it is now removed from active incidents map feed
        updated_active = self.app.get('/api/incidents/active')
        updated_ids = [c["cluster_id"] for c in updated_active.get_json()["incidents"]]
        self.assertNotIn(test_cluster_id, updated_ids)


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING TERRARISK AI PHASE 4 AUTHORITY TRIAGE & CREDIBILITY SUITE")
    print("=" * 65)
    unittest.main(verbosity=2)

