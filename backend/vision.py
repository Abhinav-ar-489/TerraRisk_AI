"""
TerraRisk AI - 3-Tier Computer Vision Hazard Verification Brain
Analyzes citizen-submitted disaster photos with hardcoded keyword-based inference:
1. Tier 1: Multimodal Vision API (Google Gemini 3.7/3.6 Flash, Groq, OpenAI) with explicit Keyword Prompting.
2. Tier 2: Built-in Python Geological Feature & Texture Engine with Clear Road Surface Guard.
3. Tier 3: Multi-Factor Heuristic & Spam Classifier (Filters solid blank memes, uniform frames, and pristine roads).
"""

import os
import io
import re
import json
import base64
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

# Ensure .env is resolved across backend directory and root workspace
_base_dir = os.path.dirname(os.path.abspath(__file__))
for _env_path in [
    os.path.join(_base_dir, ".env"),
    os.path.join(_base_dir, "..", ".env"),
    os.path.join(_base_dir, "..", "backend", ".env"),
    ".env"
]:
    if os.path.exists(_env_path):
        load_dotenv(_env_path, override=False)

try:
    from PIL import Image, ImageStat, ImageFilter
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ==============================================================================
# 🔑 HARDCODED INCIDENT KEYWORD DEFINITIONS (SPECIFIC TO EVERY INCIDENT CATEGORY)
# ==============================================================================
INCIDENT_KEYWORD_RULES = {
    "mud_crack": {
        "true_keyword": "INCIDENT_MUD_CRACK_TRUE",
        "false_keyword": "INCIDENT_MUD_CRACK_FALSE",
        "title": "Mud Crack / Surface Fissure",
        "status_label_true": "✓ Mud Crack Hazard Confirmed",
        "status_label_false": "⚠️ No Mud Cracks / Fissures Detected",
        "desc": "ground tensile fissure, soil fracture, open earth rupture on hillside or road"
    },
    "rockfall": {
        "true_keyword": "INCIDENT_ROCKFALL_TRUE",
        "false_keyword": "INCIDENT_ROCKFALL_FALSE",
        "title": "Rockfall / Debris Roll",
        "status_label_true": "✓ Rockfall / Debris Hazard Confirmed",
        "status_label_false": "⚠️ No Fallen Rocks / Debris Detected",
        "desc": "fallen boulders, shattered stone debris, scree tumble across roadway or slope"
    },
    "stream_overflow": {
        "true_keyword": "INCIDENT_STREAM_OVERFLOW_TRUE",
        "false_keyword": "INCIDENT_STREAM_OVERFLOW_FALSE",
        "title": "Stream Overflow / Flash Flood",
        "status_label_true": "✓ Stream Overflow / Flooding Confirmed",
        "status_label_false": "⚠️ No Stream Overflow / Flooding Detected",
        "desc": "turbid torrential floodwaters, overflowing riverbanks, inundated culverts or road"
    },
    "blocked_road": {
        "true_keyword": "INCIDENT_BLOCKED_ROAD_TRUE",
        "false_keyword": "INCIDENT_BLOCKED_ROAD_FALSE",
        "title": "Blocked Roadway",
        "status_label_true": "✓ Blocked Roadway Hazard Confirmed",
        "status_label_false": "⚠️ Clear Paved Road Detected (No Obstruction)",
        "desc": "highway obstructed by mudslide, fallen trees, rock debris, or pavement collapse"
    },
    "slope_movement": {
        "true_keyword": "INCIDENT_SLOPE_MOVEMENT_TRUE",
        "false_keyword": "INCIDENT_SLOPE_MOVEMENT_FALSE",
        "title": "Slope Movement / Landslide",
        "status_label_true": "✓ Hillside Slope Movement / Landslide Confirmed",
        "status_label_false": "⚠️ Stable Slope (No Active Movement)",
        "desc": "active mass wasting escarpment, hillside subsidence, mud flow, rotational hill slip"
    }
}


def _extract_image_bytes(image_input: Any) -> Optional[bytes]:
    """Parse raw bytes from base64 data URI, raw base64 string, or bytes object."""
    if not image_input:
        return None
    if isinstance(image_input, bytes):
        return image_input
    if isinstance(image_input, str):
        if "," in image_input and "base64" in image_input:
            image_input = image_input.split(",", 1)[1]
        try:
            return base64.b64decode(image_input)
        except Exception:
            return None
    return None


_OLLAMA_VISION_CHECKED = False
_INSTALLED_VISION_MODEL = None


def _get_active_ollama_vision_model() -> Optional[str]:
    global _OLLAMA_VISION_CHECKED, _INSTALLED_VISION_MODEL
    if _OLLAMA_VISION_CHECKED:
        return _INSTALLED_VISION_MODEL
    _OLLAMA_VISION_CHECKED = True
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=0.4)
        if res.status_code == 200:
            models = [m.get("name", "") for m in res.json().get("models", [])]
            for candidate in ["moondream", "moondream:latest", "llava", "llava:7b", "llama3.2-vision:11b", "minicpm-v"]:
                if any(candidate in m for m in models):
                    _INSTALLED_VISION_MODEL = candidate
                    return _INSTALLED_VISION_MODEL
    except Exception:
        pass
    _INSTALLED_VISION_MODEL = None
    return None


def interpret_keyword_response(raw_output: str, reported_hazard: str, default_engine: str = "llm-vision") -> Dict[str, Any]:
    """
    Interprets the LLM inference output by checking structured JSON fields and decision keywords.
    Prioritizes negative/rejection signals to eliminate false positives.
    """
    rule = INCIDENT_KEYWORD_RULES.get(reported_hazard, INCIDENT_KEYWORD_RULES["mud_crack"])
    text_up = raw_output.upper()
    
    # 1. Parse structured JSON if present
    parsed = {}
    m = re.search(r'\{[\s\S]*\}', raw_output)
    if m:
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            pass

    is_gen = None

    # Priority A: Check explicit boolean in parsed JSON
    if "is_genuine_hazard" in parsed and isinstance(parsed["is_genuine_hazard"], bool):
        is_gen = parsed["is_genuine_hazard"]

    # Priority B: Check explicit keyword in parsed JSON
    if is_gen is None and "keyword" in parsed:
        kw = str(parsed["keyword"]).upper().strip()
        if rule["false_keyword"] in kw or "FALSE" in kw or "REJECT" in kw or "SAFE" in kw:
            is_gen = False
        elif rule["true_keyword"] in kw or "TRUE" in kw or "CONFIRM" in kw:
            is_gen = True

    # Priority C: Keyword regex scan in raw text (negative signals checked before positive)
    if is_gen is None:
        has_specific_false = rule["false_keyword"] in text_up
        has_specific_true = rule["true_keyword"] in text_up
        has_generic_false = any(term in text_up for term in [
            "HAZARD_VERIFIED_FALSE", "HAZARD_FALSE", "CLEAR_UNDAMAGED_ROAD", "NON_HAZARD",
            "\"IS_GENUINE_HAZARD\": FALSE", "\"IS_GENUINE_HAZARD\":FALSE"
        ])
        has_generic_true = any(term in text_up for term in [
            "HAZARD_VERIFIED_TRUE", "HAZARD_TRUE",
            "\"IS_GENUINE_HAZARD\": TRUE", "\"IS_GENUINE_HAZARD\":TRUE"
        ])

        if has_specific_false and not has_specific_true:
            is_gen = False
        elif has_specific_true and not has_specific_false:
            is_gen = True
        elif has_generic_false and not has_generic_true:
            is_gen = False
        elif has_generic_true and not has_generic_false:
            is_gen = True
        else:
            # Conservative default: if ambiguous, mark false
            is_gen = False if (has_specific_false or has_generic_false) else bool(parsed.get("is_genuine_hazard", False))

    matched_keyword = rule["true_keyword"] if is_gen else rule["false_keyword"]
    status_label = rule["status_label_true"] if is_gen else rule["status_label_false"]
    conf = float(parsed.get("confidence_score", 0.92 if is_gen else 0.08))
    sev = int(parsed.get("suggested_severity", 3 if is_gen else 1))
    summary = str(parsed.get("ai_summary", status_label))

    return {
        "is_genuine_hazard": is_gen,
        "keyword": matched_keyword,
        "status_text": status_label,
        "confidence_score": round(conf, 2),
        "detected_hazard": reported_hazard if is_gen else "non_hazard_scene",
        "suggested_severity": sev,
        "ai_summary": summary,
        "is_spam": not is_gen,
        "engine": default_engine
    }


def _query_gemini_vision(img_bytes: bytes, reported_hazard: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Query Google Gemini Multimodal Vision API directly with rigorous anti-false-positive instructions."""
    gemini_models = [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash"
    ]
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
    
    rule = INCIDENT_KEYWORD_RULES.get(reported_hazard, INCIDENT_KEYWORD_RULES["mud_crack"])
    true_kw = rule["true_keyword"]
    false_kw = rule["false_keyword"]
    
    system_instruction = (
        f"You are the Official Kerala Disaster Management (KSDMA) Computer Vision Inference Engine.\n"
        f"A citizen uploaded this field photo reporting disaster incident type: '{reported_hazard}' ({rule['title']}).\n\n"
        f"TASK:\n"
        f"Examine the visual evidence carefully to classify whether this is a GENUINE DISASTER HAZARD or a NON-HAZARD / FALSE ALARM.\n\n"
        f"RIGOROUS CLASSIFICATION RULES:\n"
        f"1. MUST BE CLASSIFIED AS FALSE / NON-HAZARD:\n"
        f"   - Indoor scenes (rooms, desks, laptops, monitors, office, furniture, ceilings, walls, beds, kitchens)\n"
        f"   - People, faces, selfies, group portraits, animals, pets, food, personal belongings, vehicles\n"
        f"   - Digital screenshots, charts, graphics, drawings, memes, icons, text documents\n"
        f"   - Pristine, clear paved roads with intact lane markings and unobstructed transit lanes\n"
        f"   - Ordinary minor municipal wear (small isolated pothole, minor sidewalk crack, ordinary rain puddle) that are NOT KSDMA catastrophic mass wasting / flash flood emergencies\n"
        f"   - Normal green gardens, lawns, trees, calm lakes or skies without disaster displacement\n\n"
        f"2. MUST BE CLASSIFIED AS TRUE / GENUINE HAZARD ONLY WHEN REAL EVIDENCE IS VISIBLE:\n"
        f"   - Ground tensile fissures, deep soil fractures, open earth rupture on hillside or road (mud_crack)\n"
        f"   - Fallen boulders, shattered stone debris, scree tumble across roadway or slope (rockfall)\n"
        f"   - Turbid torrential floodwaters, overflowing riverbanks, inundated culverts or road (stream_overflow)\n"
        f"   - Highway obstructed by mudslide, fallen trees, rock debris, or pavement collapse (blocked_road)\n"
        f"   - Active hillside landslide, slope subsidence, mud flow, rotational hill slip (slope_movement)\n\n"
        f"MANDATORY OUTPUT KEYWORDS:\n"
        f"- If GENUINE HAZARD: output keyword [{true_kw}] with is_genuine_hazard: true\n"
        f"- If FALSE / NON-HAZARD / SAFE: output keyword [{false_kw}] with is_genuine_hazard: false\n\n"
        f"Respond strictly in valid JSON matching this schema:\n"
        f"{{\n"
        f"  \"keyword\": \"{true_kw}\" or \"{false_kw}\",\n"
        f"  \"is_genuine_hazard\": true or false,\n"
        f"  \"confidence_score\": <float 0.80 to 0.99 for true hazard, 0.02 to 0.25 for false>,\n"
        f"  \"detected_hazard\": \"{reported_hazard}\" or \"non_hazard_scene\",\n"
        f"  \"suggested_severity\": <int 1 to 5>,\n"
        f"  \"ai_summary\": \"<Concise 1-2 sentence geotechnical observation detailing observable evidence or reason for rejection>\"\n"
        f"}}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": system_instruction},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_b64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 400
        }
    }

    for model_name in gemini_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            resp = requests.post(url, json=payload, timeout=8.5)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [])[0]
                content = cand.get("content", {}).get("parts", [])[0].get("text", "{}")
                return interpret_keyword_response(content, reported_hazard, default_engine=f"google-{model_name}")
            elif resp.status_code == 429:
                # Quota rate-limited on this model tier, seamlessly continue to next candidate
                continue
            elif resp.status_code == 404:
                # Model name not supported in this endpoint version
                continue
            else:
                continue
        except Exception:
            continue

    return None


def _query_openai_or_groq_vision(img_bytes: bytes, reported_hazard: str, api_key: str, is_groq: bool = False) -> Optional[Dict[str, Any]]:
    """Query OpenAI GPT-4o-mini or Groq Llama-3.2-Vision with strict anti-false-positive instructions."""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions" if is_groq else "https://api.openai.com/v1/chat/completions"
        model_name = "llama-3.2-11b-vision-preview" if is_groq else "gpt-4o-mini"
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        rule = INCIDENT_KEYWORD_RULES.get(reported_hazard, INCIDENT_KEYWORD_RULES["mud_crack"])
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt_text = (
            f"You are a disaster geotechnical vision classifier for KSDMA. Citizen reported incident: '{reported_hazard}'.\n"
            f"Strictly classify as FALSE / NON-HAZARD if image is indoor room, office desk, selfie, screenshot, food, vehicle, or pristine road.\n"
            f"If genuine hazard, output keyword [{rule['true_keyword']}] and is_genuine_hazard: true.\n"
            f"If non-hazard, output keyword [{rule['false_keyword']}] and is_genuine_hazard: false.\n"
            f"Return JSON: {{\"keyword\": string, \"is_genuine_hazard\": bool, \"detected_hazard\": string, \"confidence_score\": float, \"suggested_severity\": int, \"ai_summary\": string}}."
        )
        
        payload = {
            "model": model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }
            ],
            "max_tokens": 250,
            "temperature": 0.1
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=5.0)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            return interpret_keyword_response(content, reported_hazard, default_engine=model_name)
    except Exception:
        pass
    return None


def _query_ollama_vision(image_b64: str, reported_hazard: str) -> Optional[Dict[str, Any]]:
    """Attempt zero-shot vision inference against local Ollama vision models with strict instructions."""
    model = _get_active_ollama_vision_model()
    if not model:
        return None
        
    rule = INCIDENT_KEYWORD_RULES.get(reported_hazard, INCIDENT_KEYWORD_RULES["mud_crack"])
    system_prompt = (
        f"You are a geotechnical disaster vision classifier for KSDMA. "
        f"Strictly classify as FALSE if image shows indoor room, desk, selfie, screenshot, or safe scene. "
        f"If genuine hazard, output keyword [{rule['true_keyword']}] with is_genuine_hazard: true. "
        f"If non-hazard, output keyword [{rule['false_keyword']}] with is_genuine_hazard: false. "
        f"Return JSON: {{\"keyword\": string, \"is_genuine_hazard\": bool, \"detected_hazard\": string, \"confidence_score\": float, \"suggested_severity\": int, \"ai_summary\": string}}."
    )
    user_prompt = f"Analyze this image. The citizen reported: '{reported_hazard}'. Output decision JSON."

    try:
        res = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": model,
                "system": system_prompt,
                "prompt": user_prompt,
                "images": [image_b64],
                "stream": False,
                "format": "json",
                "options": {"num_predict": 150, "temperature": 0.1}
            },
            timeout=4.0
        )
        if res.status_code == 200:
            body = res.json().get('response', '')
            return interpret_keyword_response(body, reported_hazard, default_engine=f"ollama-{model}")
    except Exception:
        pass
    return None


def _query_multimodal_vision_api(img_bytes: bytes, reported_hazard: str) -> Optional[Dict[str, Any]]:
    """Check environment for Vision LLM API keys and invoke direct Multimodal Vision API."""
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        res = _query_gemini_vision(img_bytes, reported_hazard, gemini_key)
        if res:
            return res

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        res = _query_openai_or_groq_vision(img_bytes, reported_hazard, openai_key, is_groq=False)
        if res:
            return res

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        res = _query_openai_or_groq_vision(img_bytes, reported_hazard, groq_key, is_groq=True)
        if res:
            return res

    # Check local Ollama
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
    ollama_res = _query_ollama_vision(img_b64, reported_hazard)
    if ollama_res:
        return ollama_res

    return None


# ==============================================================================
# 🛡️ MULTI-STAGE LOCAL ZERO-DEPENDENCY COMPUTER VISION PRE-FILTERS
# ==============================================================================

def _detect_pristine_undamaged_road(image: Any) -> tuple[bool, str]:
    """Carefully checks if an image is a PRISTINE, COMPLETELY UNDAMAGED paved road."""
    try:
        img_rgb = image.convert("RGB").resize((256, 256))
        img_gray = img_rgb.convert("L")
        arr_rgb = np.array(img_rgb, dtype=float)
        arr_gray = np.array(img_gray, dtype=float)

        # Lower center roadway zone (y: 110-245, x: 50-205)
        road_zone_rgb = arr_rgb[110:245, 50:205, :]
        road_zone_gray = arr_gray[110:245, 50:205]
        r_z = road_zone_rgb[:, :, 0]
        g_z = road_zone_rgb[:, :, 1]
        b_z = road_zone_rgb[:, :, 2]

        diff_rg = np.abs(r_z - g_z)
        diff_gb = np.abs(g_z - b_z)
        diff_rb = np.abs(r_z - b_z)

        # Asphalt neutrality: R, G, B are very close (slate dark gray)
        asphalt_neutrality = (diff_rg < 16) & (diff_gb < 16) & (diff_rb < 16) & (r_z > 30) & (r_z < 155)
        asphalt_ratio = float(np.mean(asphalt_neutrality))

        # Check for painted road markings (yellow double center lines, white edge lines)
        yellow_pixels = (arr_rgb[:, :, 0] > 155) & (arr_rgb[:, :, 1] > 125) & (arr_rgb[:, :, 2] < 120) & ((arr_rgb[:, :, 0] - arr_rgb[:, :, 2]) > 35)
        yellow_count = int(np.sum(yellow_pixels))

        white_pixels = (arr_rgb[:, :, 0] > 180) & (arr_rgb[:, :, 1] > 180) & (arr_rgb[:, :, 2] > 180)
        white_count = int(np.sum(white_pixels))

        has_lane_markings = (yellow_count >= 25) or (white_count >= 60)

        # Check for cracks and fissures on the road surface
        dark_crack_pixels = np.mean(road_zone_gray < 22.0)
        
        # High-contrast edge filtering on the road zone
        road_crop = img_gray.crop((50, 110, 205, 245))
        road_edges = road_crop.filter(ImageFilter.FIND_EDGES)
        road_edge_mean = float(ImageStat.Stat(road_edges).mean[0])

        mud_pixels = (r_z > 70) & (r_z > g_z * 1.2) & (g_z > b_z)
        mud_ratio = float(np.mean(mud_pixels))
        road_std = float(np.std(road_zone_gray))

        is_pristine = (
            (asphalt_ratio > 0.35) and
            (has_lane_markings) and
            (dark_crack_pixels < 0.02) and
            (mud_ratio < 0.06) and
            (road_edge_mean < 18.0) and
            (road_std < 32.0)
        )

        if is_pristine:
            return True, "Clear paved highway with intact lane markings and unobstructed travel lanes."

        return False, ""
    except Exception:
        return False, ""


def _detect_screenshot_or_graphic(image: Any) -> tuple[bool, str]:
    """Detects digital screenshots, documents, software UI, or graphic illustrations."""
    try:
        img_rgb = image.convert("RGB").resize((128, 128))
        arr = np.array(img_rgb, dtype=float)
        
        # 1. Pure digital whites / darks ratio (dominant in screenshots/docs/UI)
        pure_white = (arr[:, :, 0] > 248) & (arr[:, :, 1] > 248) & (arr[:, :, 2] > 248)
        pure_dark = (arr[:, :, 0] < 12) & (arr[:, :, 1] < 12) & (arr[:, :, 2] < 12)
        digital_background_ratio = float(np.mean(pure_white | pure_dark))
        if digital_background_ratio > 0.30:
            return True, "Digital screenshot or software graphic interface detected with uniform digital background."

        # 2. Extreme low unique color count (vector drawings, digital charts, icons)
        colors = img_rgb.getcolors(maxcolors=200)
        if colors is not None and len(colors) < 64:
            return True, "Digital graphic or illustration detected with restricted digital palette."

        return False, ""
    except Exception:
        return False, ""


def _detect_human_or_selfie(image: Any) -> tuple[bool, str]:
    """Detects human skin tones / portraits / selfies."""
    try:
        img_rgb = image.convert("RGB").resize((128, 128))
        arr = np.array(img_rgb, dtype=float)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]

        # Normalized RGB + YCbCr skin tone detection locus
        cb = -0.1687 * r - 0.3313 * g + 0.5 * b + 128
        cr = 0.5 * r - 0.4187 * g - 0.0813 * b + 128

        skin_pixels = (
            (r > 90) & (g > 40) & (b > 20) &
            (r > g) & (r > b) &
            ((r - g) > 12) & (np.abs(r - b) > 10) &
            (cb >= 77) & (cb <= 127) &
            (cr >= 133) & (cr <= 173)
        )

        # Check central upper region (where faces typically reside in selfies/portraits)
        center_skin = skin_pixels[20:100, 30:98]
        skin_ratio = float(np.mean(center_skin))
        total_skin_ratio = float(np.mean(skin_pixels))

        # A portrait/selfie has a localized face in the center (skin_ratio > 0.25) surrounded by hair/background (total_skin < 0.70).
        # A field of dirt or soil has uniform brown earth covering the whole frame (>0.70), which is NOT a face.
        if skin_ratio > 0.25 and total_skin_ratio < 0.70:
            return True, "Personal portrait or selfie photo detected with prominent human facial/skin tones."

        return False, ""
    except Exception:
        return False, ""


def _detect_indoor_office_scene(image: Any) -> tuple[bool, str]:
    """Detects indoor rooms, office desks, monitors, walls, ceilings, and furniture."""
    try:
        img_rgb = image.convert("RGB").resize((128, 128))
        arr = np.array(img_rgb, dtype=float)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]

        gray = img_rgb.convert("L")
        gray_arr = np.array(gray, dtype=float)
        
        # Check for large uniform painted wall / ceiling blocks (low gradient regions)
        gx = np.abs(np.diff(gray_arr, axis=1))
        gy = np.abs(np.diff(gray_arr, axis=0))
        flat_regions = (gx[:-1, :] < 3.0) & (gy[:, :-1] < 3.0)
        flat_ratio = float(np.mean(flat_regions))

        # Check indoor neutral/warm color profile
        color_diff = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
        neutral_pixels = color_diff < 22.0
        neutral_ratio = float(np.mean(neutral_pixels))

        if flat_ratio > 0.38 and neutral_ratio > 0.30:
            return True, "Indoor architectural space (room/desk/wall) detected with uniform painted surfaces and artificial lighting."

        return False, ""
    except Exception:
        return False, ""


def _detect_calm_undamaged_outdoor(image: Any, reported_hazard: str) -> tuple[bool, str]:
    """Detects peaceful green lawns, garden grass, or calm scenes without terrain displacement."""
    try:
        img_rgb = image.convert("RGB").resize((128, 128))
        arr = np.array(img_rgb, dtype=float)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]

        # Healthy green grass/vegetation: green dominates red and blue significantly
        green_grass = (g > 60) & (g > r * 1.15) & (g > b * 1.25)
        grass_ratio = float(np.mean(green_grass))

        # Check for soil rupture / muddy displacement
        gray = img_rgb.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_intensity = float(ImageStat.Stat(edges).mean[0])

        if grass_ratio > 0.50 and edge_intensity < 14.0:
            if reported_hazard in ["mud_crack", "slope_movement", "rockfall", "blocked_road"]:
                return True, "Undamaged green lawn/vegetation with no soil displacement, fractures, or fallen debris."

        return False, ""
    except Exception:
        return False, ""


def _python_geological_feature_engine(img_bytes: bytes, reported_hazard: str) -> Dict[str, Any]:
    """
    Zero-dependency Python geological texture, entropy, and spectral classifier.
    Employs multi-stage negative pre-filters and conservative ground-truth validation.
    """
    rule = INCIDENT_KEYWORD_RULES.get(reported_hazard, INCIDENT_KEYWORD_RULES["mud_crack"])
    true_kw = rule["true_keyword"]
    false_kw = rule["false_keyword"]

    if not PIL_AVAILABLE:
        return {
            "is_genuine_hazard": False,
            "keyword": false_kw,
            "status_text": rule["status_label_false"],
            "detected_hazard": "unverified_scene",
            "confidence_score": 0.20,
            "suggested_severity": 1,
            "ai_summary": "Unverified field telemetry (imaging library unavailable). Flagged for manual review.",
            "is_spam": True,
            "engine": "fallback-unverified"
        }

    try:
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        # --- 1. MULTI-STAGE NEGATIVE PRE-FILTERS ---

        # 1a. Pristine undamaged road filter
        is_clean_road, clean_road_msg = _detect_pristine_undamaged_road(image)
        if is_clean_road:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "clear_undamaged_road",
                "confidence_score": 0.08,
                "suggested_severity": 1,
                "ai_summary": clean_road_msg,
                "is_spam": True,
                "engine": "python-heuristic-road-guard"
            }

        # 1b. Monochrome / blank photo filter
        stat = ImageStat.Stat(image.resize((64, 64)))
        r_std, g_std, b_std = stat.stddev[:3]
        if r_std < 4.0 and g_std < 4.0 and b_std < 4.0:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "blank_image",
                "confidence_score": 0.05,
                "suggested_severity": 1,
                "ai_summary": "Image flagged as solid blank or monochrome photo with no visible geological features.",
                "is_spam": True,
                "engine": "python-heuristic-spam-filter"
            }

        # 1c. Screenshot / digital graphic filter
        is_graphic, graphic_msg = _detect_screenshot_or_graphic(image)
        if is_graphic:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "digital_graphic",
                "confidence_score": 0.06,
                "suggested_severity": 1,
                "ai_summary": graphic_msg,
                "is_spam": True,
                "engine": "python-heuristic-graphic-filter"
            }

        # 1d. Human selfie / portrait filter
        is_selfie, selfie_msg = _detect_human_or_selfie(image)
        if is_selfie:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "portrait_selfie",
                "confidence_score": 0.05,
                "suggested_severity": 1,
                "ai_summary": selfie_msg,
                "is_spam": True,
                "engine": "python-heuristic-portrait-filter"
            }

        # 1e. Indoor room / office scene filter
        is_indoor, indoor_msg = _detect_indoor_office_scene(image)
        if is_indoor:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "indoor_scene",
                "confidence_score": 0.08,
                "suggested_severity": 1,
                "ai_summary": indoor_msg,
                "is_spam": True,
                "engine": "python-heuristic-indoor-filter"
            }

        # 1f. Calm undamaged green lawn / foliage filter
        is_calm, calm_msg = _detect_calm_undamaged_outdoor(image, reported_hazard)
        if is_calm:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "calm_outdoor_scene",
                "confidence_score": 0.10,
                "suggested_severity": 1,
                "ai_summary": calm_msg,
                "is_spam": True,
                "engine": "python-heuristic-lawn-guard"
            }

        # --- 2. SPECIFIC DISASTER GEOLOGICAL FEATURE ANALYSIS ---
        image_resized = image.resize((256, 256))
        stat256 = ImageStat.Stat(image_resized)
        r_mean, g_mean, b_mean = stat256.mean[:3]
        
        gray_img = image_resized.convert("L")
        edge_img = gray_img.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edge_img)
        edge_intensity = edge_stat.mean[0]

        np_arr = np.array(gray_img, dtype=float)
        texture_roughness = float(np.std(np_arr))

        # Check geological color signatures
        is_earth_toned = (r_mean >= g_mean * 0.95) and (r_mean > 50 and r_mean < 210) and (b_mean < g_mean)
        is_water_chroma = (b_mean > 80 and abs(r_mean - g_mean) < 40) or (r_mean > 70 and g_mean > 65 and b_mean < 95)
        
        is_hazard_confirmed = False
        confidence = 0.20
        severity = 1
        summary = rule["status_label_false"]

        if reported_hazard == "mud_crack":
            # Real tensile ground fissures require high edge density on earth-toned or asphalt ground
            if (is_earth_toned and edge_intensity > 6.0 and texture_roughness > 14.0) or edge_intensity > 18.0:
                is_hazard_confirmed = True
                confidence = 0.84
                severity = 4 if edge_intensity > 25.0 else 3
                summary = f"Visual surface cracks and fissures confirmed on terrain (Edge Intensity: {edge_intensity:.1f})."
            else:
                summary = "Pavement/soil surface does not exhibit prominent tension fissure patterns."

        elif reported_hazard == "rockfall":
            # Real rockfall requires jagged high texture roughness and angular debris contrast
            if texture_roughness > 22.0 and edge_intensity > 14.0:
                is_hazard_confirmed = True
                confidence = 0.86
                severity = 4 if edge_intensity > 25.0 else 3
                summary = f"Loose boulders and shattered stone debris detected on transit corridor (Roughness: {texture_roughness:.1f})."
            else:
                summary = "No loose boulders or shattered rock tumble patterns identified."

        elif reported_hazard == "stream_overflow":
            # Real stream overflow requires water chroma and fluid texture
            if is_water_chroma and edge_intensity > 8.0:
                is_hazard_confirmed = True
                confidence = 0.85
                severity = 4 if edge_intensity > 18.0 else 3
                summary = "Turbid water flow and stream overflow indicators detected in disaster corridor."
            else:
                summary = "No torrential stream overflow or active floodwater accumulation observed."

        elif reported_hazard == "blocked_road":
            if edge_intensity > 16.0 and texture_roughness > 20.0:
                is_hazard_confirmed = True
                confidence = 0.82
                severity = 3
                summary = "Transit route obstruction patterns detected across transit corridor."
            else:
                summary = "Roadway appears open with no major landslide debris obstruction."

        elif reported_hazard == "slope_movement":
            if is_earth_toned and texture_roughness > 18.0 and edge_intensity > 12.0:
                is_hazard_confirmed = True
                confidence = 0.85
                severity = 4 if edge_intensity > 22.0 else 3
                summary = "Active hillside displacement and mass wasting evidence confirmed on terrain."
            else:
                summary = "Hillside slope appears stable with no visible mass wasting escarpment."

        # If not confirmed, default conservatively to non-hazard
        if not is_hazard_confirmed:
            return {
                "is_genuine_hazard": False,
                "keyword": false_kw,
                "status_text": rule["status_label_false"],
                "detected_hazard": "non_hazard_scene",
                "confidence_score": 0.12,
                "suggested_severity": 1,
                "ai_summary": summary,
                "is_spam": True,
                "engine": "python-heuristic-conservative"
            }

        return {
            "is_genuine_hazard": True,
            "keyword": true_kw,
            "status_text": rule["status_label_true"],
            "detected_hazard": reported_hazard,
            "confidence_score": round(confidence, 2),
            "suggested_severity": severity,
            "ai_summary": summary,
            "is_spam": False,
            "engine": "python-heuristic-geological"
        }

    except Exception as e:
        return {
            "is_genuine_hazard": False,
            "keyword": false_kw,
            "status_text": rule["status_label_false"],
            "detected_hazard": "unverified_scene",
            "confidence_score": 0.15,
            "suggested_severity": 1,
            "ai_summary": f"Telemetry processing error: {e}. Flagged for authority manual review.",
            "is_spam": True,
            "engine": "fallback-safe-unverified"
        }


def analyze_hazard_image(image_input: Any, reported_hazard: str = "slope_movement") -> Dict[str, Any]:
    """
    Main entry point for Computer Vision Hazard Classification.
    Attempts Multimodal Vision LLM API (Gemini / OpenAI / Groq) first;
    Falls back gracefully to the Python Geological & Terrain Engine.
    Always returns exact hardcoded keywords for the specific incident type.
    """
    rule = INCIDENT_KEYWORD_RULES.get(reported_hazard, INCIDENT_KEYWORD_RULES["mud_crack"])
    
    if not image_input:
        return {
            "is_genuine_hazard": True,
            "keyword": rule["true_keyword"],
            "status_text": rule["status_label_true"],
            "detected_hazard": reported_hazard,
            "confidence_score": 0.75,
            "suggested_severity": 3,
            "ai_summary": "Citizen field report logged without photographic attachment.",
            "is_spam": False,
            "engine": "text-only"
        }

    raw_bytes = _extract_image_bytes(image_input)
    if not raw_bytes:
        return {
            "is_genuine_hazard": True,
            "keyword": rule["true_keyword"],
            "status_text": rule["status_label_true"],
            "detected_hazard": reported_hazard,
            "confidence_score": 0.70,
            "suggested_severity": 3,
            "ai_summary": "Standard field report telemetry.",
            "is_spam": False,
            "engine": "format-fallback"
        }

    # 1. Attempt Multimodal Vision LLM API (Gemini / OpenAI / Groq / Ollama)
    vision_api_res = _query_multimodal_vision_api(raw_bytes, reported_hazard)
    if vision_api_res:
        return vision_api_res

    # 2. Built-in Python Geological CV Engine (Resilient zero-downtime fallback)
    return _python_geological_feature_engine(raw_bytes, reported_hazard)


if __name__ == "__main__":
    print("[INFO] Testing TerraRisk AI Computer Vision Brain with Hardcoded Keywords...")
    for haz in INCIDENT_KEYWORD_RULES:
        res = analyze_hazard_image(None, haz)
        print(f"[{haz}] -> Keyword: {res['keyword']}")
