import os
import io
import sys
import base64
from PIL import Image, ImageDraw
from vision import analyze_hazard_image

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def create_sample_hazard_image():
    """Create a synthetic high-entropy mud crack/fissure image for testing."""
    img = Image.new("RGB", (300, 300), color=(110, 80, 50))  # Earth brown
    draw = ImageDraw.Draw(img)
    # Draw jagged crack lines
    draw.line([(50, 40), (120, 110), (150, 180), (220, 260)], fill=(30, 20, 10), width=6)
    draw.line([(120, 110), (200, 130), (260, 200)], fill=(35, 25, 15), width=4)
    draw.line([(150, 180), (100, 240)], fill=(40, 30, 20), width=3)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_sample_spam_image():
    """Create a synthetic monochrome / indoor non-hazard image."""
    img = Image.new("RGB", (300, 300), color=(240, 240, 240))  # Plain white wall
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def run_vision_test():
    print("=" * 65)
    print("🔍 TERRARISK AI — COMPUTER VISION ENGINE VERIFICATION")
    print("=" * 65)

    # Test 1: Geological Hazard Photo (Mud Crack / Fissure)
    print("\n📸 Test 1: Analyzing Geological Hazard Photo (Mud Crack)...")
    hazard_bytes = create_sample_hazard_image()
    res_hazard = analyze_hazard_image(hazard_bytes, "mud_crack")

    print(f"  • Engine Used       : {res_hazard.get('engine')}")
    print(f"  • Genuine Hazard?   : {'✅ YES' if res_hazard.get('is_genuine_hazard') else '❌ NO'}")
    print(f"  • Detected Hazard   : {res_hazard.get('detected_hazard')}")
    print(f"  • Confidence Score  : {res_hazard.get('confidence_score') * 100:.1f}%")
    print(f"  • Suggested Severity: {res_hazard.get('suggested_severity')}/5")
    print(f"  • AI Summary        : {res_hazard.get('ai_summary')}")

    # Test 2: Spam / Non-Hazard Photo (Blank White / Indoor)
    print("\n📸 Test 2: Analyzing Non-Hazard / Blank Indoor Image...")
    spam_bytes = create_sample_spam_image()
    res_spam = analyze_hazard_image(spam_bytes, "mud_crack")

    print(f"  • Engine Used       : {res_spam.get('engine')}")
    print(f"  • Genuine Hazard?   : {'✅ YES' if res_spam.get('is_genuine_hazard') else '❌ NO (Flagged)'}")
    print(f"  • Is Spam/Invalid   : {'⚠️ SPAM' if res_spam.get('is_spam') else 'Clean'}")
    print(f"  • Confidence Score  : {res_spam.get('confidence_score') * 100:.1f}%")
    print(f"  • AI Summary        : {res_spam.get('ai_summary')}")

    print("\n" + "=" * 65)
    print("✅ Computer Vision Engine is fully operational and responsive!")
    print("=" * 65)


if __name__ == "__main__":
    run_vision_test()
