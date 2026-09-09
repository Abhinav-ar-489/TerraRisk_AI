import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import init_db, create_incident_report, get_shelter_by_id, calculate_haversine_distance
from routing import calculate_evacuation_route, check_polyline_safety

TEST_DB = os.path.join(os.path.dirname(__file__), "data", "test_reroute_guarantee.db")


class TestSafeReroutingGuarantee(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_PATH"] = TEST_DB
        init_db(db_path=TEST_DB)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def test_01_guaranteed_bypass_of_incident_on_road(self):
        """Verify that when an incident is right on the direct path, the route reroutes with 0 collisions."""
        # Evacuating from Kalpetta north (11.6200, 76.0500) to Meppadi Shelter (11.5510, 76.1280), ~11.5 km corridor
        start_lat, start_lng = 11.6200, 76.0500
        shelter = get_shelter_by_id(1, db_path=TEST_DB)
        dest_lat, dest_lng = shelter["lat"], shelter["lng"]

        # Insert a major landslide incident directly midway on the highway
        mid_lat = round((start_lat + dest_lat) / 2.0, 5)
        mid_lng = round((start_lng + dest_lng) / 2.0, 5)

        inc_id = create_incident_report(
            user_id=1,
            hazard_type="blocked_road",
            lat=mid_lat,
            lng=mid_lng,
            description="Active landslide blocking direct highway path",
            severity=5,
            db_path=TEST_DB
        )

        route = calculate_evacuation_route(start_lat, start_lng, destination_shelter_id=1, db_path=TEST_DB)
        self.assertTrue(route["success"])
        self.assertTrue(route["safe_route_guarantee"])
        self.assertEqual(route["collision_count"], 0)
        self.assertGreaterEqual(route["avoided_hazards_count"], 1)

        # Check polyline directly against the incident midpoint
        poly = route["route_polyline"]
        self.assertGreaterEqual(len(poly), 2)
        for pt in poly:
            d = calculate_haversine_distance(pt[0], pt[1], mid_lat, mid_lng)
            # Must maintain safety clearance (> 1.2 km away from hazard center)
            self.assertGreater(d, 1.2, f"Route point {pt} came too close to hazard at ({mid_lat}, {mid_lng}): {d} km")

        print("\n  [PASS] Verified 100% collision-free route bypassing active incident on road.")

    def test_02_guaranteed_bypass_of_known_accident_blackspots(self):
        """Verify known disaster/accident blackspots are strictly bypassed."""
        # Route from Vythiri (11.5500, 76.0400) to Kalpetta Shelter 2 (11.6080, 76.0825)
        start_lat, start_lng = 11.5500, 76.0400
        route = calculate_evacuation_route(start_lat, start_lng, destination_shelter_id=2, db_path=TEST_DB)
        self.assertTrue(route["success"])
        self.assertEqual(route["collision_count"], 0)
        self.assertTrue(route["safe_route_guarantee"])
        print("  [PASS] Verified known accident-prone blackspots are completely bypassed.")


if __name__ == "__main__":
    unittest.main()
