"""
TerraRisk AI - Phase 6 Verification Suite
Tests 48-Hour Temporal Risk Projection endpoint, rainfall accumulation, saturation escalation,
and ML risk trajectory across Kerala topography.
"""

import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from server import app


class TestPhase6TemporalRiskAndGIS(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_01_temporal_risk_endpoint_structure(self):
        """Verify /api/forecast/temporal-risk returns 6 intervals spanning 0h to 48h."""
        res = self.app.post('/api/forecast/temporal-risk', json={
            "lat": 11.5542,
            "lng": 76.1308,
            "slope": 42.0,
            "elevation": 1120.0,
            "soil": 1,
            "current_rainfall": 45.0,
            "current_saturation": 75.0,
            "rain_trend": 1.5
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("timeline", data)
        timeline = data["timeline"]
        self.assertEqual(len(timeline), 6)

        hours = [t["hour"] for t in timeline]
        self.assertEqual(hours, [0, 6, 12, 24, 36, 48])

    def test_02_cumulative_rainfall_and_risk_escalation(self):
        """Verify cumulative precipitation and predicted risk strictly escalate over time on steep terrain."""
        res = self.app.post('/api/forecast/temporal-risk', json={
            "lat": 11.6920,
            "lng": 76.1450,
            "slope": 38.5,
            "elevation": 950.0,
            "soil": 1,
            "current_rainfall": 50.0,
            "current_saturation": 80.0,
            "rain_trend": 2.0
        })
        data = res.get_json()
        timeline = data["timeline"]

        for i in range(len(timeline) - 1):
            curr_step = timeline[i]
            next_step = timeline[i + 1]
            self.assertLessEqual(curr_step["cumulative_rainfall"], next_step["cumulative_rainfall"])
            self.assertLessEqual(curr_step["soil_saturation"], next_step["soil_saturation"])

        step_48h = timeline[-1]
        self.assertGreaterEqual(step_48h["cumulative_rainfall"], 300.0)
        self.assertEqual(step_48h["level"], "Critical Threat")
        self.assertEqual(step_48h["level_color"], "#EF4444")

    def test_03_lowland_guard_remains_nominal_across_timeline(self):
        """Verify gentle lowlands (<8 deg, <150m) remain safely suppressed even with heavy rain simulation."""
        res = self.app.post('/api/forecast/temporal-risk', json={
            "lat": 9.9312,
            "lng": 76.2673,
            "slope": 1.5,
            "elevation": 12.0,
            "soil": 3,
            "current_rainfall": 50.0,
            "current_saturation": 60.0
        })
        data = res.get_json()
        timeline = data["timeline"]
        for step in timeline:
            self.assertLessEqual(step["risk_percentage"], 5.0)
            self.assertEqual(step["level"], "Nominal Stability")


if __name__ == "__main__":
    unittest.main(verbosity=2)
