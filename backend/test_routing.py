import os
import sys
import unittest
import json
import sqlite3
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import (
    init_db,
    get_shelter_by_id,
    update_shelter_occupancy,
    get_nearby_shelters,
    create_incident_report,
    verify_incident_cluster
)
from routing import (
    calculate_evacuation_route,
    calculate_bearing,
    bearing_to_direction,
    point_to_segment_distance,
    generate_hazard_detour_point
)
from server import app, generate_jwt_token

TEST_DB = os.path.join(os.path.dirname(__file__), "data", "test_routing_disaster.db")


class TestEvacuationRouting(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_PATH"] = TEST_DB
        init_db(db_path=TEST_DB)
        cls.app = app
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def test_01_shelter_occupancy_updates_and_clamping(self):
        """Test shelter occupancy update with bounds clamping [0, capacity]."""
        # Get first default shelter (e.g. Meppadi GHSS, capacity 300)
        shelter = get_shelter_by_id(1, db_path=TEST_DB)
        self.assertIsNotNone(shelter)
        capacity = shelter["capacity"]

        # 1. Update to valid occupancy
        res = update_shelter_occupancy(1, 120, db_path=TEST_DB)
        self.assertTrue(res["success"])
        self.assertEqual(res["occupied"], 120)
        self.assertEqual(res["available_spots"], capacity - 120)

        # 2. Test upper clamp (occupied > capacity)
        res_over = update_shelter_occupancy(1, capacity + 50, db_path=TEST_DB)
        self.assertTrue(res_over["success"])
        self.assertEqual(res_over["occupied"], capacity)
        self.assertEqual(res_over["available_spots"], 0)

        # 3. Test lower clamp (occupied < 0)
        res_neg = update_shelter_occupancy(1, -10, db_path=TEST_DB)
        self.assertTrue(res_neg["success"])
        self.assertEqual(res_neg["occupied"], 0)
        self.assertEqual(res_neg["available_spots"], capacity)

    def test_02_geodetic_geometry_and_bearing_helpers(self):
        """Test math helpers for bearing calculation and compass directions."""
        bearing_north = calculate_bearing(10.0, 76.0, 11.0, 76.0)
        self.assertAlmostEqual(bearing_north, 0.0, delta=1.0)
        self.assertEqual(bearing_to_direction(bearing_north), "North")

        bearing_east = calculate_bearing(10.0, 76.0, 10.0, 77.0)
        self.assertAlmostEqual(bearing_east, 90.0, delta=2.0)
        self.assertEqual(bearing_to_direction(bearing_east), "East")

        # Point to segment distance
        dist = point_to_segment_distance(10.0, 76.5, 10.0, 76.0, 10.0, 77.0)
        self.assertLess(dist, 0.1)

    def test_03_evacuation_routing_fallback_and_detour(self):
        """Test evacuation route calculation with hazard avoidance detour generation."""
        start_lat, start_lng = 11.5542, 76.1308
        dest_shelter = get_shelter_by_id(1, db_path=TEST_DB)

        # 1. Direct route calculation
        route = calculate_evacuation_route(start_lat, start_lng, destination_shelter_id=1, db_path=TEST_DB)
        self.assertTrue(route["success"])
        self.assertGreater(route["total_distance_km"], 0.0)
        self.assertGreater(route["estimated_time_mins"], 0)
        self.assertGreaterEqual(len(route["route_polyline"]), 2)
        self.assertGreaterEqual(len(route["turn_by_turn"]), 2)

        # 2. Inject an active verified hazard directly in corridor
        mid_lat = (start_lat + dest_shelter["lat"]) / 2.0
        mid_lng = (start_lng + dest_shelter["lng"]) / 2.0
        c_id = create_incident_report(
            user_id=1,
            hazard_type="blocked_road",
            lat=mid_lat,
            lng=mid_lng,
            description="Major debris blockage across main highway",
            severity=5,
            db_path=TEST_DB
        )
        verify_incident_cluster(c_id, verified_by_user_id=1, db_path=TEST_DB)

        # Calculate route again -> should detect danger zone and apply detour
        detour_route = calculate_evacuation_route(start_lat, start_lng, destination_shelter_id=1, db_path=TEST_DB)
        self.assertTrue(detour_route["success"])
        self.assertGreaterEqual(detour_route["avoided_hazards_count"], 1)
        self.assertIn("Hazard Detour Applied", detour_route["safety_status"])

    def test_04_server_evacuation_api_endpoints(self):
        """Test POST /api/routes/evacuate and POST /api/shelters/update-occupancy API routes."""
        # 1. Public Evacuation Planning Endpoint
        resp = self.client.post("/api/routes/evacuate", json={
            "start_lat": 11.5361,
            "start_lng": 76.1667,
            "destination_shelter_id": 1
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("route_polyline", data)
        self.assertIn("turn_by_turn", data)

        # 2. GET /api/shelters
        shelters_resp = self.client.get("/api/shelters?lat=11.5361&lng=76.1667")
        self.assertEqual(shelters_resp.status_code, 200)
        shelters_data = shelters_resp.get_json()
        self.assertTrue(shelters_data["success"])
        self.assertGreater(shelters_data["count"], 0)

        # 3. Unauthorized Occupancy Update -> 401
        unauth_resp = self.client.post("/api/shelters/update-occupancy", json={
            "shelter_id": 1,
            "occupied": 85
        })
        self.assertEqual(unauth_resp.status_code, 401)

        # 4. Authorized Authority Admin Occupancy Update -> 200
        admin_user = {
            "id": 1,
            "name": "District Collector",
            "phone": "+919999999999",
            "role": "Authority_Admin"
        }
        token = generate_jwt_token(admin_user)
        auth_resp = self.client.post("/api/shelters/update-occupancy", json={
            "shelter_id": 1,
            "occupied": 150
        }, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(auth_resp.status_code, 200)
        res_json = auth_resp.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["occupied"], 150)


if __name__ == "__main__":
    unittest.main()
