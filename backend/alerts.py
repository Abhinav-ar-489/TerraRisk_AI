"""
TerraRisk AI - Multi-Channel Zero-Cost Alert Synthesis & CAP v1.2 Engine
Dispatches emergency disaster warnings across:
1. Telegram Emergency Channel Bot (100% Free)
2. WhatsApp Disaster Ward & Panchayat Group Broadcast Generator
3. Native Cellular SMS & Twilio Hybrid Fallback
4. OASIS / NDMA / ITU-T X.1303 Common Alerting Protocol (CAP v1.2) XML & JSON standard feeds.
"""

import os
import time
import json
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests

# Twilio SMS credentials from environment
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# Telegram Bot Credentials (Optional, 100% free)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# In-memory store for recent active emergency broadcasts
ACTIVE_BROADCASTS: List[Dict[str, Any]] = []

# Bilingual standard templates for instant, zero-latency fallback
FALLBACK_TEMPLATES = {
    "mud_crack": {
        "name_en": "Mud Crack / Slope Tension Fissure",
        "name_ml": "മണ്ണിലെ വിള്ളലുകൾ / ഭ്രംശങ്ങൾ",
        "en": "URGENT WARNING: Expanding tension cracks & soil displacement detected at {location}. Slope collapse threat within {radius_km}km perimeter. Evacuate to nearest shelter immediately.",
        "ml": "അടിയന്തര മുന്നറിയിപ്പ്: {location} പ്രദേശത്ത് മണ്ണിൽ വലിയ വിള്ളലുകൾ കണ്ടെത്തിയിരിക്കുന്നു. {radius_km} കി.മീ ചുറ്റളവിൽ മണ്ണിടിച്ചിൽ സാധ്യത. ഉടൻ സുരക്ഷിത കേന്ദ്രങ്ങളിലേക്ക് മാറുക."
    },
    "stream_overflow": {
        "name_en": "Stream Overflow / Flash Torrent",
        "name_ml": "അരുവി കരകവിഞ്ഞൊഴുകൽ / മിന്നൽ പ്രളയം",
        "en": "FLASH FLOOD ALERT: Raging stream overflow & drainage blockages at {location}. Flash torrent risk within {radius_km}km. Avoid low-lying banks and transit routes.",
        "ml": "മിന്നൽ പ്രളയ മുന്നറിയിപ്പ്: {location} പ്രദേശത്ത് മലവെള്ളപ്പാച്ചിലും ജലനിരപ്പ് ഉയരലും. {radius_km} കി.മീ ചുറ്റളവിലുള്ളവർ പുഴയോരങ്ങളിൽ നിന്ന് മാറുക."
    },
    "rockfall": {
        "name_en": "Rockfall / Scree Boulder Roll",
        "name_ml": "പാറ വീഴ്ച / കല്ലിടിച്ചിൽ",
        "en": "ROCKFALL ALERT: Active boulder tumble & scree movement on slopes at {location}. Road corridors within {radius_km}km restricted. Seek safe high ground.",
        "ml": "പാറ വീഴ്ചാ മുന്നറിയിപ്പ്: {location} മലയോരങ്ങളിൽ പാറകളും കല്ലുകളും പതിക്കുന്നു. {radius_km} കി.മീ ചുറ്റളവിലുള്ള റോഡുകൾ ഒഴിവാക്കുക."
    },
    "blocked_road": {
        "name_en": "Blocked Roadway / Transit Obstruction",
        "name_ml": "റോഡ് തടസ്സം / ഗതാഗത തടസ്സം",
        "en": "TRANSIT HAZARD: Major roadway obstructed by debris and fallen trees near {location}. Emergency vehicles only within {radius_km}km. Reroute travel.",
        "ml": "ഗതാഗത മുന്നറിയിപ്പ്: {location} സമീപം റോഡിൽ മണ്ണും മരങ്ങളും വീണ് ഗതാഗതം തടസ്സപ്പെട്ടു. {radius_km} കി.മീ ചുറ്റളവിൽ മറ്റ് വഴികൾ ഉപയോഗിക്കുക."
    },
    "slope_movement": {
        "name_en": "Active Slope Creep / Landslide Mass",
        "name_ml": "ഉരുൾപൊട്ടൽ / സജീവ മണ്ണിടിച്ചിൽ",
        "en": "CRITICAL EVACUATION: Active hill subsidence and rapid slope mass movement at {location}. Extreme landslide threat within {radius_km}km. Evacuate immediately!",
        "ml": "അതീവ ജാഗ്രതാ നിർദ്ദേശം: {location} പ്രദേശത്ത് സജീവ ഉരുൾപൊട്ടൽ / മണ്ണിടിച്ചിൽ സാധ്യത. {radius_km} കി.മീ ചുറ്റളവിലുള്ളവർ ഉടൻ സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക!"
    }
}


def synthesize_bilingual_alert(
    hazard_type: str,
    location_name: str,
    severity: int = 3,
    radius_km: float = 5.0
) -> Dict[str, str]:
    """
    Synthesize structured emergency alert text in both English and Malayalam.
    Attempts local Ollama LLaMA 3.2 inference first, then falls back to verified templates.
    """
    hazard_type = hazard_type if hazard_type in FALLBACK_TEMPLATES else "slope_movement"
    fallback_data = FALLBACK_TEMPLATES[hazard_type]
    
    default_en = fallback_data["en"].format(location=location_name, radius_km=radius_km)
    default_ml = fallback_data["ml"].format(location=location_name, radius_km=radius_km)
    
    # Try calling Ollama llama3.2:3b
    try:
        system_prompt = (
            "You are the Kerala State Disaster Management Authority (KSDMA) emergency alert synthesizer. "
            "Generate an ultra-concise emergency alert in English AND in Malayalam. "
            "Output JSON with two keys: 'alert_en' and 'alert_ml'. "
            "Do NOT include conversational text, only valid JSON."
        )
        user_prompt = (
            f"Hazard: {fallback_data['name_en']} ({hazard_type})\n"
            f"Location: {location_name}\n"
            f"Severity Level: {severity}/5\n"
            f"Evacuation Danger Radius: {radius_km} km\n"
            f"Instructions: Advise immediate evacuation to nearest relief shelter."
        )
        
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "llama3.2:3b",
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "format": "json",
                "options": {"num_predict": 120, "temperature": 0.1}
            },
            timeout=1.8
        )
        
        if response.status_code == 200:
            parsed = json.loads(response.json().get('response', '{}'))
            alert_en = parsed.get('alert_en', '').strip()
            alert_ml = parsed.get('alert_ml', '').strip()
            if alert_en and alert_ml:
                return {"alert_en": alert_en, "alert_ml": alert_ml, "source": "ollama-llama3.2"}
    except Exception:
        pass
        
    return {
        "alert_en": default_en,
        "alert_ml": default_ml,
        "source": "template-verified"
    }


def dispatch_telegram_broadcast(
    alert_en: str,
    alert_ml: str,
    lat: float,
    lng: float,
    radius_km: float,
    hazard_type: str = "slope_movement"
) -> Dict[str, Any]:
    """
    Post structured bilingual emergency alert to Telegram disaster broadcast channel.
    Also builds instant public Telegram share link.
    """
    maps_url = f"https://maps.google.com/?q={lat:.5f},{lng:.5f}"
    hazard_title = FALLBACK_TEMPLATES.get(hazard_type, {}).get("name_en", "Geological Hazard")
    
    tg_text = (
        f"🚨 *TERRARISK AI — EMERGENCY DISASTER BULLETIN*\n"
        f"⚠️ *Threat*: {hazard_title}\n"
        f"📍 *Sector*: ({lat:.4f}°N, {lng:.4f}°E)\n"
        f"🔴 *Danger Perimeter*: {radius_km} km Radius\n"
        f"🗺️ *Live Map*: {maps_url}\n\n"
        f"🇬🇧 *English Alert*:\n{alert_en}\n\n"
        f"🇮🇳 *മലയാളം മുന്നറിയിപ്പ്*:\n{alert_ml}\n\n"
        f"ℹ️ _Issued by Kerala State Disaster Management Cell_"
    )
    
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(maps_url)}&text={urllib.parse.quote(tg_text)}"
    
    delivered = False
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
        try:
            tg_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            res = requests.post(tg_api_url, json={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": tg_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }, timeout=3.0)
            if res.status_code == 200:
                delivered = True
        except Exception:
            pass
            
    return {
        "success": True,
        "channel_delivered": delivered,
        "share_url": share_url,
        "formatted_text": tg_text
    }


def generate_whatsapp_broadcast_link(
    alert_en: str,
    alert_ml: str,
    lat: float,
    lng: float,
    radius_km: float,
    hazard_type: str = "slope_movement"
) -> str:
    """
    Generate ready-to-share WhatsApp broadcast deep-link for Panchayat & Village ward groups.
    """
    maps_url = f"https://maps.google.com/?q={lat:.5f},{lng:.5f}"
    hazard_title = FALLBACK_TEMPLATES.get(hazard_type, {}).get("name_en", "Geological Hazard")
    
    wa_message = (
        f"🚨 *TERRARISK DISASTER ALERT ({radius_km}km Radius)*\n"
        f"⚠️ Hazard: {hazard_title}\n"
        f"📍 Location: {maps_url}\n\n"
        f"🇬🇧 English:\n{alert_en}\n\n"
        f"🇮🇳 മലയാളം:\n{alert_ml}\n\n"
        f"⚠️ Evacuate to nearest shelter immediately!"
    )
    return f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_message)}"


def dispatch_multi_channel_alert(
    lat: float,
    lng: float,
    radius_km: float,
    alert_en: str,
    alert_ml: str,
    hazard_type: str = "slope_movement",
    sender_name: str = "KSDMA Emergency Command",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unified multi-channel emergency broadcast dispatcher:
    1. Telegram Channel & Instant Link
    2. WhatsApp Panchayat Share Link
    3. Twilio SMS / Simulated Local Dispatch
    4. CAP Standard Feeds & Audit Logging
    """
    from database import get_users_in_radius, log_audit_action, save_emergency_broadcast
    
    recipients = get_users_in_radius(lat=lat, lng=lng, radius_km=radius_km, db_path=db_path)
    combined_message = f"🚨 KSDMA ALERT ({radius_km}km Radius):\n{alert_en}\n---\n{alert_ml}"
    
    # 1. Telegram Dispatch
    tg_result = dispatch_telegram_broadcast(alert_en, alert_ml, lat, lng, radius_km, hazard_type)
    
    # 2. WhatsApp Group Broadcast Link
    wa_link = generate_whatsapp_broadcast_link(alert_en, alert_ml, lat, lng, radius_km, hazard_type)
    
    # 3. Cellular SMS Dispatch (Twilio / Simulated)
    delivered = []
    twilio_ready = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)
    twilio_client = None
    if twilio_ready:
        try:
            from twilio.rest import Client
            twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception:
            twilio_ready = False
            
    for user in recipients:
        phone = user.get("phone", "")
        if not phone:
            continue
            
        if twilio_ready and twilio_client:
            try:
                msg = twilio_client.messages.create(
                    body=combined_message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone
                )
                delivered.append({"user_id": user["id"], "phone": phone, "sid": msg.sid, "status": "sent", "channel": "cellular_sms"})
            except Exception as e:
                delivered.append({"user_id": user["id"], "phone": phone, "sid": f"sim_tw_{int(time.time())}_{user['id']}", "status": "simulated", "channel": "cellular_simulated", "note": str(e)})
        else:
            delivered.append({"user_id": user["id"], "phone": phone, "sid": f"sim_sms_{int(time.time())}_{user['id']}", "status": "simulated_delivered", "channel": "cellular_simulated"})
            
    # 4. Record Active Broadcast
    broadcast_id = f"bcast_{int(time.time())}_{int(lat*100)}_{int(lng*100)}"
    broadcast_record = {
        "broadcast_id": broadcast_id,
        "lat": lat,
        "lng": lng,
        "radius_km": radius_km,
        "hazard_type": hazard_type,
        "alert_en": alert_en,
        "alert_ml": alert_ml,
        "recipients_count": len(delivered),
        "sender": sender_name,
        "telegram_link": tg_result["share_url"],
        "whatsapp_link": wa_link,
        "sent_at": datetime.now(timezone.utc).isoformat()
    }
    ACTIVE_BROADCASTS.append(broadcast_record)
    try:
        save_emergency_broadcast(broadcast_record, db_path=db_path)
    except Exception as err:
        print(f"[WARNING] Could not persist broadcast to DB: {err}")
    
    # 5. Audit log
    log_audit_action(
        "MULTI_CHANNEL_ALERT_DISPATCHED",
        details=f"Broadcast ID: {broadcast_id} | Coords: ({lat:.4f}, {lng:.4f}) | Radius: {radius_km}km | Recipients: {len(delivered)} | Hazard: {hazard_type}",
        db_path=db_path
    )
    
    return {
        "success": True,
        "broadcast_id": broadcast_id,
        "radius_km": radius_km,
        "recipients_count": len(delivered),
        "delivered": delivered,
        "alert_en": alert_en,
        "alert_ml": alert_ml,
        "telegram_share_url": tg_result["share_url"],
        "whatsapp_share_url": wa_link,
        "dispatched_at": broadcast_record["sent_at"]
    }


def dispatch_geofenced_sms(
    lat: float,
    lng: float,
    radius_km: float,
    alert_en: str,
    alert_ml: str,
    hazard_type: str = "slope_movement",
    sender_name: str = "KSDMA Emergency Command",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Compatibility alias calling unified multi-channel dispatcher."""
    return dispatch_multi_channel_alert(
        lat=lat, lng=lng, radius_km=radius_km, alert_en=alert_en, alert_ml=alert_ml,
        hazard_type=hazard_type, sender_name=sender_name, db_path=db_path
    )


def get_active_broadcasts(hours_window: float = 24.0, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    now_ts = time.time()
    cutoff_ts = now_ts - (hours_window * 3600)
    
    # Fetch persisted records from SQLite database first
    try:
        from database import get_persisted_emergency_broadcasts
        persisted = get_persisted_emergency_broadcasts(hours_window=hours_window, db_path=db_path)
    except Exception:
        persisted = []
        
    seen_ids = set()
    valid_broadcasts = []
    
    # Merge memory broadcasts (latest first)
    for b in reversed(ACTIVE_BROADCASTS):
        bid = b.get("broadcast_id")
        if bid and bid not in seen_ids:
            try:
                sent_dt = datetime.fromisoformat(b["sent_at"].replace('Z', '+00:00'))
                if sent_dt.timestamp() >= cutoff_ts:
                    seen_ids.add(bid)
                    valid_broadcasts.append(b)
            except Exception:
                seen_ids.add(bid)
                valid_broadcasts.append(b)
                
    # Merge persisted database broadcasts
    for p in persisted:
        pid = p.get("broadcast_id")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            valid_broadcasts.append(p)
            
    return valid_broadcasts


def generate_cap_xml(incidents: List[Dict[str, Any]], broadcasts: List[Dict[str, Any]]) -> str:
    """Generate standardized OASIS / ITU-T X.1303 CAP v1.2 XML feed."""
    root = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
    sent_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    
    ET.SubElement(root, "identifier").text = f"TERRARISK-CAP-{int(time.time())}"
    ET.SubElement(root, "sender").text = "ksdma-alert-engine@kerala.gov.in"
    ET.SubElement(root, "sent").text = sent_time
    ET.SubElement(root, "status").text = "Actual"
    ET.SubElement(root, "msgType").text = "Alert"
    ET.SubElement(root, "scope").text = "Public"
    
    items = []
    for b in broadcasts:
        items.append({
            "id": b["broadcast_id"],
            "lat": b["lat"],
            "lng": b["lng"],
            "radius_km": b["radius_km"],
            "hazard_type": b.get("hazard_type", "slope_movement"),
            "desc_en": b["alert_en"],
            "desc_ml": b["alert_ml"],
            "severity": "Extreme",
            "urgency": "Immediate"
        })
        
    for inc in incidents:
        if inc.get("status") == "verified":
            items.append({
                "id": inc["cluster_id"],
                "lat": inc["lat"],
                "lng": inc["lng"],
                "radius_km": 2.5,
                "hazard_type": inc.get("primary_hazard_type", "slope_movement"),
                "desc_en": f"Verified {inc.get('primary_hazard_type', '').replace('_', ' ')} incident reported.",
                "desc_ml": "സ്ഥിരീകരിച്ച പ്രകൃതി ദുരന്ത മുന്നറിയിപ്പ്.",
                "severity": "Severe" if inc.get("max_severity", 3) >= 4 else "Moderate",
                "urgency": "Expected"
            })
            
    for it in items:
        # Info block 1: English
        info_en = ET.SubElement(root, "info")
        ET.SubElement(info_en, "language").text = "en-IN"
        ET.SubElement(info_en, "category").text = "Geo"
        ET.SubElement(info_en, "event").text = it["hazard_type"].replace('_', ' ').title()
        ET.SubElement(info_en, "urgency").text = it["urgency"]
        ET.SubElement(info_en, "severity").text = it["severity"]
        ET.SubElement(info_en, "certainty").text = "Observed"
        ET.SubElement(info_en, "headline").text = f"Landslide/Debris Threat: {it['hazard_type'].replace('_', ' ').title()}"
        ET.SubElement(info_en, "description").text = it["desc_en"]
        area_en = ET.SubElement(info_en, "area")
        ET.SubElement(area_en, "areaDesc").text = f"Sector ({it['lat']:.4f}N, {it['lng']:.4f}E)"
        ET.SubElement(area_en, "circle").text = f"{it['lat']:.4f},{it['lng']:.4f} {it['radius_km']}"
        
        # Info block 2: Malayalam
        info_ml = ET.SubElement(root, "info")
        ET.SubElement(info_ml, "language").text = "ml-IN"
        ET.SubElement(info_ml, "category").text = "Geo"
        ET.SubElement(info_ml, "event").text = it["hazard_type"]
        ET.SubElement(info_ml, "urgency").text = it["urgency"]
        ET.SubElement(info_ml, "severity").text = it["severity"]
        ET.SubElement(info_ml, "certainty").text = "Observed"
        ET.SubElement(info_ml, "headline").text = "ഉരുൾപൊട്ടൽ / മണ്ണിടിച്ചിൽ അടിയന്തര മുന്നറിയിപ്പ്"
        ET.SubElement(info_ml, "description").text = it["desc_ml"]
        area_ml = ET.SubElement(info_ml, "area")
        ET.SubElement(area_ml, "areaDesc").text = f"പ്രദേശം ({it['lat']:.4f}N, {it['lng']:.4f}E)"
        ET.SubElement(area_ml, "circle").text = f"{it['lat']:.4f},{it['lng']:.4f} {it['radius_km']}"
        
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')


def generate_cap_json(incidents: List[Dict[str, Any]], broadcasts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate standardized CAP v1.2 JSON representation."""
    sent_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    
    entries = []
    for b in broadcasts:
        entries.append({
            "identifier": b["broadcast_id"],
            "sent": b["sent_at"],
            "status": "Actual",
            "msgType": "Alert",
            "scope": "Public",
            "hazard_type": b.get("hazard_type", "slope_movement"),
            "coordinates": {"lat": b["lat"], "lng": b["lng"], "radius_km": b["radius_km"]},
            "alerts": {
                "en": b["alert_en"],
                "ml": b["alert_ml"]
            },
            "channels": {
                "telegram": b.get("telegram_link"),
                "whatsapp": b.get("whatsapp_link")
            }
        })
        
    return {
        "cap_version": "1.2",
        "authority": "Kerala State Disaster Management Authority (KSDMA)",
        "sender": "ksdma-emergency-ops@kerala.gov.in",
        "generated_at": sent_time,
        "active_alerts_count": len(entries),
        "alerts": entries
    }
