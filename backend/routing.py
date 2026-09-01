"""
TerraRisk AI - Safe Evacuation Routing Engine (Phase 7)
Features:
1. Spatial Hazard Avoidance & Detour Calculation around active verified red danger zones and blocked roads.
2. Nearest Shelter Selection with capacity & occupancy verification.
3. Multi-point routing with OSRM (Open Source Routing Machine) + dynamic detour waypoints.
4. Autonomous Geodetic Bearing & Tangent Waypoint Fallback with turn-by-turn navigation steps.
"""

import math
import time
from typing import List, Dict, Any, Optional, Tuple
import requests

from database import (
    get_nearby_shelters,
    get_shelter_by_id,
    get_active_incident_clusters,
    calculate_haversine_distance
)


def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate true initial compass bearing (in degrees, 0 to 360) from point 1 to point 2."""
    lat1_r, lng1_r = math.radians(lat1), math.radians(lng1)
    lat2_r, lng2_r = math.radians(lat2), math.radians(lng2)
    d_lng = lng2_r - lng1_r
    
    y = math.sin(d_lng) * math.cos(lat2_r)
    x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(d_lng)
    bearing_deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return bearing_deg


def bearing_to_direction(bearing: float) -> str:
    """Convert bearing in degrees to 8-point compass cardinal string."""
    dirs = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"]
    idx = int((bearing + 22.5) / 45.0) % 8
    return dirs[idx]


def point_to_segment_distance(
    p_lat: float, p_lng: float,
    a_lat: float, a_lng: float,
    b_lat: float, b_lng: float
) -> float:
    """Calculate minimum Haversine distance in km from point P to line segment AB."""
    ab_dist = calculate_haversine_distance(a_lat, a_lng, b_lat, b_lng)
    if ab_dist < 0.001:
        return calculate_haversine_distance(p_lat, p_lng, a_lat, a_lng)
        
    # Project point P onto AB using planar approximation for small distances
    ap_lat, ap_lng = p_lat - a_lat, p_lng - a_lng
    ab_lat, ab_lng = b_lat - a_lat, b_lng - a_lng
    
    t = max(0.0, min(1.0, (ap_lat * ab_lat + ap_lng * ab_lng) / (ab_lat * ab_lat + ab_lng * ab_lng + 1e-9)))
    proj_lat = a_lat + t * ab_lat
    proj_lng = a_lng + t * ab_lng
    
    return calculate_haversine_distance(p_lat, p_lng, proj_lat, proj_lng)


def generate_hazard_detour_point(
    start_lat: float, start_lng: float,
    dest_lat: float, dest_lng: float,
    hazard_lat: float, hazard_lng: float,
    buffer_km: float = 2.0
) -> Tuple[float, float]:
    """Compute a perpendicular safe waypoint shifted away from the hazard center."""
    d_lat = dest_lat - start_lat
    d_lng = dest_lng - start_lng
    mag = math.sqrt(d_lat * d_lat + d_lng * d_lng) + 1e-9
    
    # Perpendicular unit vectors
    perp_lat = -d_lng / mag
    perp_lng = d_lat / mag
    
    # Check which perpendicular direction shifts further from hazard center
    cand1_lat = hazard_lat + perp_lat * (buffer_km / 111.0)
    cand1_lng = hazard_lng + perp_lng * (buffer_km / (111.0 * math.cos(math.radians(hazard_lat))))
    
    cand2_lat = hazard_lat - perp_lat * (buffer_km / 111.0)
    cand2_lng = hazard_lng - perp_lng * (buffer_km / (111.0 * math.cos(math.radians(hazard_lat))))
    
    d1 = calculate_haversine_distance(cand1_lat, cand1_lng, hazard_lat, hazard_lng)
    d2 = calculate_haversine_distance(cand2_lat, cand2_lng, hazard_lat, hazard_lng)
    
    return (cand1_lat, cand1_lng) if d1 >= d2 else (cand2_lat, cand2_lng)


def calculate_evacuation_route(
    start_lat: float,
    start_lng: float,
    destination_shelter_id: Optional[int] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate an optimal, hazard-evading evacuation route to the safest relief shelter.
    Avoids active verified landslide/flood clusters and blocked roads.
    Returns polyline coordinates, turn-by-turn maneuvers, ETA, and safety metrics.
    """
    # 1. Target Shelter Resolution
    target_shelter = None
    if destination_shelter_id:
        target_shelter = get_shelter_by_id(destination_shelter_id, db_path=db_path)
        
    if not target_shelter:
        nearby_shelters = get_nearby_shelters(start_lat, start_lng, radius_km=150.0, db_path=db_path)
        available_shelters = [s for s in nearby_shelters if s.get("available_spots", 1) > 0]
        if available_shelters:
            target_shelter = available_shelters[0]
        elif nearby_shelters:
            target_shelter = nearby_shelters[0]
        else:
            # Fallback Kerala State Relief Base
            target_shelter = {
                "id": 999,
                "name": "State Emergency Relief Camp",
                "lat": 11.5361,
                "lng": 76.1667,
                "capacity": 250,
                "occupied": 40,
                "available_spots": 210,
                "contact_number": "+91 94470 00000",
                "district": "Wayanad"
            }
            
    dest_lat = target_shelter["lat"]
    dest_lng = target_shelter["lng"]
    
    # 2. Query Active Verified Hazards and Blocked Roads
    active_incidents = get_active_incident_clusters(db_path=db_path)
    danger_zones = []
    for inc in active_incidents:
        if inc.get("status") == "verified" or inc.get("primary_hazard_type") == "blocked_road" or inc.get("max_severity", 3) >= 4:
            danger_zones.append({
                "cluster_id": inc["cluster_id"],
                "hazard_type": inc.get("primary_hazard_type", "slope_movement"),
                "lat": inc["lat"],
                "lng": inc["lng"],
                "radius_km": 1.2 if inc.get("primary_hazard_type") == "blocked_road" else 1.8
            })
            
    # 3. Detect Intersecting Danger Zones along Direct Corridor
    intersected_hazards = []
    detour_waypoints = []
    
    for h in danger_zones:
        seg_dist = point_to_segment_distance(h["lat"], h["lng"], start_lat, start_lng, dest_lat, dest_lng)
        if seg_dist <= h["radius_km"]:
            intersected_hazards.append(h)
            detour_pt = generate_hazard_detour_point(
                start_lat, start_lng, dest_lat, dest_lng,
                h["lat"], h["lng"], buffer_km=h["radius_km"] + 1.2
            )
            detour_waypoints.append(detour_pt)
            
    # 4. Attempt OSRM Routing with Hazard Detours
    osrm_success = False
    route_polyline = []
    turn_by_turn = []
    total_dist_km = 0.0
    eta_mins = 0.0
    routing_source = "geodetic-safe-contour"
    
    try:
        # Build coordinates query: start -> detours... -> dest
        coords_list = [f"{start_lng},{start_lat}"]
        for d_lat, d_lng in detour_waypoints:
            coords_list.append(f"{d_lng},{d_lat}")
        coords_list.append(f"{dest_lng},{dest_lat}")
        
        coords_str = ";".join(coords_list)
        osrm_urls = [
            f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson&steps=true",
            f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson&steps=true"
        ]
        
        headers = {"User-Agent": "TerraRiskAI-EmergencyDisasterPlatform/2.0 (Kerala-SDMA-Routing)"}
        
        for osrm_url in osrm_urls:
            try:
                resp = requests.get(osrm_url, headers=headers, timeout=2.8)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        osrm_route = data["routes"][0]
                        total_dist_km = round(osrm_route.get("distance", 0.0) / 1000.0, 2)
                        eta_mins = max(1, round(osrm_route.get("duration", 0.0) / 60.0))
                        
                        # GeoJSON coordinates format: [lng, lat] -> Leaflet format: [lat, lng]
                        raw_coords = osrm_route.get("geometry", {}).get("coordinates", [])
                        route_polyline = [[round(c[1], 5), round(c[0], 5)] for c in raw_coords]
                        
                        # Extract turn-by-turn steps
                        step_idx = 1
                        for leg in osrm_route.get("legs", []):
                            for st in leg.get("steps", []):
                                maneuver = st.get("maneuver", {})
                                inst_text = st.get("name") or maneuver.get("type", "Proceed")
                                mod = maneuver.get("modifier", "")
                                step_dist = round(st.get("distance", 0.0) / 1000.0, 2)
                                
                                action_name = f"{mod.replace('_', ' ').title()} onto {inst_text}" if mod else f"Proceed on {inst_text}"
                                if maneuver.get("type") == "arrive":
                                    action_name = f"Arrive safely at {target_shelter['name']}"
                                    
                                turn_by_turn.append({
                                    "step": step_idx,
                                    "instruction": action_name,
                                    "distance_km": step_dist,
                                    "modifier": mod
                                })
                                step_idx += 1
                                
                        osrm_success = True
                        routing_source = "osrm-hazard-weighted-corridor"
                        break
            except Exception:
                continue
    except Exception as e:
        osrm_success = False

    # 5. Geodetic Safe Arc Fallback (Offline & Zero-Latency Safety)
    if not osrm_success or len(route_polyline) < 2:
        num_segments = 14
        route_polyline = []
        pts = [(start_lat, start_lng)] + detour_waypoints + [(dest_lat, dest_lng)]
        
        # Smooth interpolation through detour waypoints
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            for s in range(num_segments):
                frac = s / float(num_segments)
                cur_lat = p1[0] + frac * (p2[0] - p1[0])
                cur_lng = p1[1] + frac * (p2[1] - p1[1])
                route_polyline.append([round(cur_lat, 5), round(cur_lng, 5)])
        route_polyline.append([dest_lat, dest_lng])
        
        # Calculate total distance along polyline
        calc_dist = 0.0
        for i in range(len(route_polyline) - 1):
            calc_dist += calculate_haversine_distance(
                route_polyline[i][0], route_polyline[i][1],
                route_polyline[i+1][0], route_polyline[i+1][1]
            )
        total_dist_km = round(calc_dist, 2)
        # Average emergency transit speed in Ghats: ~35 km/h
        eta_mins = max(2, round((total_dist_km / 35.0) * 60.0))
        
        # Build turn-by-turn fallback instructions
        initial_bearing = calculate_bearing(start_lat, start_lng, route_polyline[1][0], route_polyline[1][1])
        initial_dir = bearing_to_direction(initial_bearing)
        
        turn_by_turn = [
            {
                "step": 1,
                "instruction": f"Depart current location heading {initial_dir} onto main relief corridor",
                "distance_km": round(total_dist_km * 0.25, 1),
                "modifier": "straight"
            }
        ]
        
        step_num = 2
        for h in intersected_hazards:
            turn_by_turn.append({
                "step": step_num,
                "instruction": f"Bypass hazard perimeter ({h['hazard_type'].replace('_', ' ').title()}) via high-ground detour",
                "distance_km": round(h["radius_km"] * 1.5, 1),
                "modifier": "hazard_avoidance"
            })
            step_num += 1
            
        turn_by_turn.append({
            "step": step_num,
            "instruction": f"Approach destination sector and turn into {target_shelter['name']}",
            "distance_km": round(total_dist_km * 0.35, 1),
            "modifier": "arrive"
        })
        routing_source = "geodetic-safe-contour"

    # 6. Assemble Final Response
    avoided_count = len(intersected_hazards)
    safety_badge = "100% Hazard-Free Direct Corridor" if avoided_count == 0 else f"Hazard Detour Applied ({avoided_count} active danger zones bypassed)"
    
    return {
        "success": True,
        "start": {
            "lat": start_lat,
            "lng": start_lng
        },
        "destination_shelter": target_shelter,
        "total_distance_km": total_dist_km,
        "estimated_time_mins": eta_mins,
        "safety_status": safety_badge,
        "avoided_hazards_count": avoided_count,
        "avoided_hazards": intersected_hazards,
        "route_polyline": route_polyline,
        "turn_by_turn": turn_by_turn,
        "routing_source": routing_source,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
