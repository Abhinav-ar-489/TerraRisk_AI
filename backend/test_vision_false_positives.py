"""
TerraRisk AI - Computer Vision False-Positive Elimination Test Suite
Evaluates vision engine accuracy against both negative false-alarm scenes
(indoor rooms, selfies, digital screenshots, clean roads, grass lawns)
and genuine disaster hazard ground-truth photos.
"""

import os
import io
import sys
import unittest
from PIL import Image, ImageDraw

# Ensure backend path is resolvable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vision import (
    analyze_hazard_image,
    _python_geological_feature_engine,
    _detect_screenshot_or_graphic,
    _detect_human_or_selfie,
    _detect_indoor_office_scene,
    _detect_calm_undamaged_outdoor,
    _detect_pristine_undamaged_road
)


def create_indoor_desk_image() -> bytes:
    """Simulates an indoor office setting: off-white painted wall, desk, and laptop."""
    img = Image.new('RGB', (200, 200), color=(235, 230, 225))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 100, 200, 200], fill=(160, 140, 120))  # wooden table
    draw.rectangle([40, 50, 150, 120], fill=(45, 45, 50))     # laptop screen
    draw.rectangle([60, 70, 130, 100], fill=(200, 220, 240))  # browser window
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def create_screenshot_image() -> bytes:
    """Simulates a computer screenshot / software UI / document."""
    img = Image.new('RGB', (200, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 190, 45], fill=(30, 30, 35))  # dark app navbar
    for y in range(60, 180, 20):
        draw.line([20, y, 170, y], fill=(100, 100, 100), width=3)  # text lines
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def create_selfie_image() -> bytes:
    """Simulates a human selfie / portrait with prominent facial skin tones."""
    img = Image.new('RGB', (200, 200), color=(90, 95, 100))
    draw = ImageDraw.Draw(img)
    # Human face with natural skin tone
    draw.ellipse([45, 30, 155, 160], fill=(215, 155, 125))
    draw.ellipse([70, 75, 90, 90], fill=(50, 30, 20))    # left eye
    draw.ellipse([110, 75, 130, 90], fill=(50, 30, 20))  # right eye
    draw.line([85, 125, 115, 125], fill=(175, 75, 65), width=4)  # mouth
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def create_clean_road_image() -> bytes:
    """Simulates a clean, pristine highway with clear lane markings."""
    img = Image.new('RGB', (256, 256), color=(80, 140, 180))  # sky
    draw = ImageDraw.Draw(img)
    # Asphalt road
    draw.polygon([(0, 256), (256, 256), (180, 110), (76, 110)], fill=(75, 75, 75))
    # Double yellow center lines
    draw.line([(125, 115), (125, 256)], fill=(230, 180, 30), width=4)
    draw.line([(131, 115), (131, 256)], fill=(230, 180, 30), width=4)
    # White edge lines
    draw.line([(85, 115), (20, 256)], fill=(240, 240, 240), width=3)
    draw.line([(171, 115), (236, 256)], fill=(240, 240, 240), width=3)
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def create_lawn_grass_image() -> bytes:
    """Simulates a peaceful green garden lawn without damage."""
    img = Image.new('RGB', (200, 200), color=(40, 145, 35))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 180, 180], fill=(45, 155, 40))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def create_ground_crack_image() -> bytes:
    """Simulates realistic dark fissure crevices on dry soil."""
    img = Image.new('RGB', (256, 256), color=(140, 95, 55))  # earth tone
    draw = ImageDraw.Draw(img)
    # Deep fracture crevices (jagged high-contrast dark lines)
    points = [
        (20, 40), (60, 80), (85, 75), (120, 130), (140, 125),
        (180, 190), (210, 185), (240, 240)
    ]
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=(15, 10, 5), width=5)
    
    # Secondary lateral branching fissures
    branches = [
        ((60, 80), (110, 65)),
        ((120, 130), (170, 100)),
        ((180, 190), (160, 240))
    ]
    for p1, p2 in branches:
        draw.line([p1, p2], fill=(20, 12, 6), width=3)

    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


class TestComputerVisionFalsePositives(unittest.TestCase):
    """Test suite ensuring zero false positives on non-hazard photos."""

    def test_01_indoor_desk_rejected(self):
        """Indoor desk / laptop photo must be rejected as non-hazard."""
        img_bytes = create_indoor_desk_image()
        res = analyze_hazard_image(img_bytes, "mud_crack")
        self.assertFalse(
            res["is_genuine_hazard"],
            f"Indoor office desk was falsely classified as genuine hazard by {res['engine']}!"
        )
        self.assertTrue(res["is_spam"])
        self.assertIn("FALSE", res["keyword"])

    def test_02_digital_screenshot_rejected(self):
        """Digital screenshot / UI diagram must be rejected as non-hazard."""
        img_bytes = create_screenshot_image()
        res = analyze_hazard_image(img_bytes, "slope_movement")
        self.assertFalse(
            res["is_genuine_hazard"],
            f"Software screenshot was falsely classified as genuine hazard by {res['engine']}!"
        )
        self.assertTrue(res["is_spam"])

    def test_03_human_selfie_rejected(self):
        """Selfie / portrait photo must be rejected as non-hazard."""
        img_bytes = create_selfie_image()
        res = analyze_hazard_image(img_bytes, "rockfall")
        self.assertFalse(
            res["is_genuine_hazard"],
            f"Selfie was falsely classified as genuine hazard by {res['engine']}!"
        )
        self.assertTrue(res["is_spam"])

    def test_04_clean_road_rejected(self):
        """Pristine paved highway with lane markings must be rejected as non-hazard."""
        img_bytes = create_clean_road_image()
        res = analyze_hazard_image(img_bytes, "blocked_road")
        self.assertFalse(
            res["is_genuine_hazard"],
            f"Clear road was falsely classified as genuine hazard by {res['engine']}!"
        )
        self.assertTrue(res["is_spam"])

    def test_05_peaceful_lawn_rejected(self):
        """Undamaged green lawn must be rejected as non-hazard."""
        img_bytes = create_lawn_grass_image()
        res = analyze_hazard_image(img_bytes, "slope_movement")
        self.assertFalse(
            res["is_genuine_hazard"],
            f"Normal grass lawn was falsely classified as genuine hazard by {res['engine']}!"
        )
        self.assertTrue(res["is_spam"])

    def test_06_genuine_mud_crack_confirmed(self):
        """Ground fissure / tensile crack photo must be confirmed by the geological engine."""
        img_bytes = create_ground_crack_image()
        res = _python_geological_feature_engine(img_bytes, "mud_crack")
        self.assertTrue(
            res["is_genuine_hazard"],
            f"Genuine soil fissure was not confirmed by {res['engine']}!"
        )
        self.assertFalse(res["is_spam"])
        self.assertIn("TRUE", res["keyword"])
        self.assertGreaterEqual(res["confidence_score"], 0.70)

    def test_07_offline_heuristic_engine_rejects_non_hazards(self):
        """Even when API is disabled, the local heuristic engine must reject non-hazards."""
        desk_bytes = create_indoor_desk_image()
        selfie_bytes = create_selfie_image()
        screen_bytes = create_screenshot_image()

        res_desk = _python_geological_feature_engine(desk_bytes, "mud_crack")
        self.assertFalse(res_desk["is_genuine_hazard"], "Local heuristic confirmed indoor desk!")

        res_selfie = _python_geological_feature_engine(selfie_bytes, "rockfall")
        self.assertFalse(res_selfie["is_genuine_hazard"], "Local heuristic confirmed selfie!")

        res_screen = _python_geological_feature_engine(screen_bytes, "slope_movement")
        self.assertFalse(res_screen["is_genuine_hazard"], "Local heuristic confirmed screenshot!")

    def test_08_real_slide_png_rejected_by_multimodal_vision(self):
        """Real PNG presentation slide from repository must be classified as non-hazard."""
        slide_path = os.path.join(os.path.dirname(__file__), "..", "presentation_assets", "slide_captures", "slide_01.png")
        if os.path.exists(slide_path):
            with open(slide_path, "rb") as f:
                slide_bytes = f.read()
            res = analyze_hazard_image(slide_bytes, "slope_movement")
            self.assertFalse(
                res["is_genuine_hazard"],
                f"Presentation slide was falsely classified as genuine hazard by {res['engine']}!"
            )
            self.assertTrue(res["is_spam"])

    def test_09_real_broken_road_confirmed_as_genuine_hazard(self):
        """Real broken road / fractured pavement must be confirmed as a genuine hazard."""
        broken_road_path = os.path.join(os.path.dirname(__file__), "test_broken_asphalt.jpg")
        if os.path.exists(broken_road_path):
            with open(broken_road_path, "rb") as f:
                img_bytes = f.read()
            res = analyze_hazard_image(img_bytes, "blocked_road")
            self.assertTrue(
                res["is_genuine_hazard"],
                f"Broken road photo was incorrectly rejected by {res['engine']}!"
            )
            self.assertFalse(res["is_spam"])
            self.assertIn("TRUE", res["keyword"])
            self.assertGreaterEqual(res["confidence_score"], 0.75)


if __name__ == "__main__":
    unittest.main(verbosity=2)
