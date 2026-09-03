import { useState, useEffect, useRef, useMemo, useCallback, Fragment } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip, Circle, Polyline, useMapEvents } from 'react-leaflet';
import { Radio, Sliders, Activity, Info, MapPin, Sun, Moon, CheckCircle, AlertTriangle, CloudRain, CloudLightning, Cloud, X, Thermometer, User, Navigation, Compass, WifiOff, PhoneCall, Menu, RefreshCw } from 'lucide-react';
import api from './services/api';
import L from 'leaflet';
import AuthModal from './components/AuthModal';
import SafetyBanner from './components/SafetyBanner';
import ReportHazardModal from './components/ReportHazardModal';
import AuthorityDashboard from './components/AuthorityDashboard';
import BroadcastAlertBanner from './components/BroadcastAlertBanner';
import MapLayersControl from './components/MapLayersControl';
import HazardHeatmapLayer from './components/HazardHeatmapLayer';
import { BASE_LAYERS, HILLSHADE_LAYER_URL } from './constants/mapLayers';
import RadarTimelinePlayer from './components/RadarTimelinePlayer';
import TerrainSlopeLegend from './components/TerrainSlopeLegend';
import EvacuationGuidanceCard from './components/EvacuationGuidanceCard';
import ShelterDetailModal from './components/ShelterDetailModal';
import ShelterOccupancyModal from './components/ShelterOccupancyModal';
import EmergencyHelplinesModal from './components/EmergencyHelplinesModal';
import MissingPersonsModal from './components/MissingPersonsModal';
import SettingsLayersModal from './components/SettingsLayersModal';
import BroadcastControlCard from './components/BroadcastControlCard';
import LeftSidebarDrawer from './components/LeftSidebarDrawer';
import MobileBottomNav from './components/MobileBottomNav';
import './App.css';

const KERALA_BOUNDS = [[8.1, 74.3], [12.9, 77.6]];

// Accurate Kerala Coastline Reference Points (lat, coast_lng)
const KERALA_COAST_POINTS = [
  [12.80, 74.85], [12.50, 74.98], [12.00, 75.15], [11.87, 75.35],
  [11.50, 75.60], [11.25, 75.77], [10.80, 75.92], [10.20, 76.15],
  [9.93, 76.26], [9.50, 76.33], [9.00, 76.53], [8.88, 76.58],
  [8.50, 76.92], [8.20, 77.08]
];

// Accurate Kerala Western Ghats Crest Points (lat, ridge_lng)
const KERALA_RIDGE_POINTS = [
  [12.80, 75.35], [12.20, 75.55], [11.80, 76.00], [11.55, 76.25],
  [11.30, 76.50], [11.00, 76.55], [10.75, 76.90], [10.40, 77.00],
  [10.15, 77.15], [9.85, 77.20], [9.50, 77.25], [9.30, 77.18],
  [9.00, 77.22], [8.75, 77.18], [8.40, 77.25], [8.20, 77.28]
];

function interpolatePolylineLat(points, lat) {
  const pts = [...points].sort((a, b) => b[0] - a[0]);
  if (lat >= pts[0][0]) return pts[0][1];
  if (lat <= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
  for (let i = 0; i < pts.length - 1; i++) {
    const [lat1, lng1] = pts[i];
    const [lat2, lng2] = pts[i + 1];
    if (lat2 <= lat && lat <= lat1) {
      const frac = (lat - lat2) / (lat1 - lat2);
      return lng2 + frac * (lng1 - lng2);
    }
  }
  return pts[pts.length - 1][1];
}

function resolveKeralaTopography(lat, lng, elevation = null) {
  const inPalakkadGap = (10.62 <= lat && lat <= 10.90) && (76.25 <= lng && lng <= 76.90);
  const cLng = interpolatePolylineLat(KERALA_COAST_POINTS, lat);
  const rLng = interpolatePolylineLat(KERALA_RIDGE_POINTS, lat);
  const width = Math.max(0.05, rLng - cLng);
  const relPos = Math.max(0.0, Math.min(1.0, (lng - cLng) / width));

  if (lng < cLng - 0.05) {
    return { elevation: 0, slope: 0.5, soil: 3 };
  }

  if (inPalakkadGap) {
    const elev = (elevation !== null && elevation > 0) ? elevation : (60.0 + relPos * 110.0);
    const slope = Math.max(1.5, Math.min(8.5, 2.0 + (relPos * 6.5)));
    return { elevation: Math.round(elev * 10) / 10, slope: Math.round(slope * 10) / 10, soil: 2 };
  }

  const isIdukki = (9.60 <= lat && lat <= 10.35) && (relPos >= 0.65);
  const isWayanad = (11.40 <= lat && lat <= 11.95) && (relPos >= 0.60);
  const isSilentValley = (10.95 <= lat && lat <= 11.35) && (relPos >= 0.65);
  const isSouthGhats = (8.40 <= lat && lat <= 9.60) && (relPos >= 0.65);

  if (elevation !== null && elevation > 0) {
    const elev = elevation;
    let slope;
    let soil;
    if (elev < 15.0) {
      slope = Math.max(0.5, 0.5 + (elev / 15.0) * 2.5);
      soil = 3;
    } else if (elev < 80.0) {
      const p = (elev - 15.0) / 65.0;
      slope = 3.0 + (p * 5.0);
      soil = elev < 35.0 ? 3 : 2;
    } else if (elev < 300.0) {
      const p = (elev - 80.0) / 220.0;
      slope = 8.0 + (p * 11.0);
      soil = 2;
    } else if (elev < 700.0) {
      const p = (elev - 300.0) / 400.0;
      slope = 19.0 + (p * 12.0);
      soil = 1;
    } else if (elev < 1200.0) {
      const p = (elev - 700.0) / 500.0;
      slope = 31.0 + (p * 10.0);
      soil = 1;
    } else {
      const p = Math.min(1.0, (elev - 1200.0) / 1200.0);
      slope = 41.0 + (p * 11.0);
      soil = 1;
    }
    return { elevation: Math.round(elev * 10) / 10, slope: Math.round(Math.min(52.0, slope) * 10) / 10, soil };
  }

  let elev;
  let slope;
  let soil;

  if (relPos < 0.15) {
    elev = 2.0 + (relPos / 0.15) * 13.0;
    slope = 0.5 + (relPos / 0.15) * 2.5;
    soil = 3;
  } else if (relPos < 0.55) {
    const p = (relPos - 0.15) / 0.40;
    elev = 15.0 + (p * 265.0);
    slope = 4.0 + (p * 14.0);
    soil = 2;
  } else {
    const p = (relPos - 0.55) / 0.45;
    if (isIdukki) {
      elev = 750.0 + (p * 1650.0);
      slope = 28.0 + (p * 20.0);
    } else if (isWayanad) {
      elev = 700.0 + (p * 650.0);
      slope = 24.0 + (p * 16.0);
    } else if (isSilentValley) {
      elev = 600.0 + (p * 1100.0);
      slope = 26.0 + (p * 18.0);
    } else if (isSouthGhats) {
      elev = 450.0 + (p * 1200.0);
      slope = 22.0 + (p * 18.0);
    } else {
      elev = 350.0 + (p * 850.0);
      slope = 20.0 + (p * 16.0);
    }
    soil = 1;
  }

  return { elevation: Math.round(elev * 10) / 10, slope: Math.round(slope * 10) / 10, soil };
}

const KERALA_NODES = [
  { id: 'Wayanad Ridge (Node A)', lat: 11.6920, lng: 76.1450, slope: 34.5, elevation: 950, soil: 1 },
  { id: 'Meppadi Sector (Node B)', lat: 11.5542, lng: 76.1308, slope: 33.0, elevation: 1120, soil: 1 },
  { id: 'Idukki Valley (Node C)', lat: 9.8492, lng: 76.9792, slope: 28.5, elevation: 650, soil: 1 },
  { id: 'Munnar Slope (Node D)', lat: 10.0889, lng: 77.0595, slope: 44.0, elevation: 1450, soil: 1 }
];

const createMarkerIcon = (isActive) => {
  return L.divIcon({
    className: 'custom-ios-marker',
    html: `<div class="${isActive ? 'ios-pulse-marker' : 'ios-static-marker'}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });
};

const createHotspotIcon = () => {
  return L.divIcon({
    className: 'custom-ios-hotspot-marker',
    html: '<div class="ios-hotspot-marker"></div>',
    iconSize: [10, 10],
    iconAnchor: [5, 5]
  });
};

const DEFAULT_HOTSPOTS = [
  { name: "Chooralmala", lat: 11.5361, lng: 76.1667, desc: "2024 Debris Flow epicenter", risk_score: 95 },
  { name: "Mundakkai", lat: 11.5167, lng: 76.1500, desc: "2024 Mass Wasting catastrophe", risk_score: 95 },
  { name: "Puthumala", lat: 11.5583, lng: 76.1308, desc: "2019 Hill-collapse zone", risk_score: 90 },
  { name: "Kavalappara", lat: 11.3622, lng: 76.2411, desc: "2019 Debris avalanche site", risk_score: 85 },
  { name: "Pettimudi", lat: 10.1683, lng: 77.0183, desc: "2020 Rajamala slide zone", risk_score: 88 },
  { name: "Meppadi", lat: 11.5500, lng: 76.1250, desc: "Critical Vulnerability Corridor", risk_score: 80 },
  { name: "Vythiri", lat: 11.5542, lng: 76.0422, desc: "High Precipitation Scarp", risk_score: 82 },
  { name: "Munnar Gap Road", lat: 10.0514, lng: 77.0988, desc: "Active Rockfall/Slump Sector", risk_score: 78 }
];

const DEFAULT_SHELTERS = [
  {
    id: 1,
    name: "Meppadi Community Relief Centre",
    lat: 11.5512,
    lng: 76.1285,
    capacity: 450,
    occupied: 120,
    contact_number: "+914936280300",
    district: "Wayanad",
    status: "active",
    in_charge_name: "Rahul M. (Revenue Officer)",
    in_charge_phone: "+919447112233"
  },
  {
    id: 2,
    name: "Nilambur Govt Higher Secondary Camp",
    lat: 11.2770,
    lng: 76.2240,
    capacity: 500,
    occupied: 95,
    contact_number: "+914831220456",
    district: "Malappuram",
    status: "active",
    in_charge_name: "Muhammed Faisal (Panchayat Sec.)",
    in_charge_phone: "+919446889900"
  },
  {
    id: 3,
    name: "Kozhikode Medical College Relief Camp",
    lat: 11.2725,
    lng: 75.8360,
    capacity: 700,
    occupied: 150,
    contact_number: "+914952350212",
    district: "Kozhikode",
    status: "active",
    in_charge_name: "Dr. K. Narayanan (Superintendent)",
    in_charge_phone: "+919447445566"
  }
];

const createGPSLocationMarkerIcon = () => {
  return L.divIcon({
    className: 'custom-ios-gps-marker-frame',
    html: `
      <div class="ios-gps-pulse-outer">
        <div class="ios-gps-pulse-core"></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });
};

const createShelterMarkerIcon = (shelter) => {
  const capacity = shelter.capacity || 100;
  const occupied = shelter.occupied || 0;
  const available = Math.max(0, capacity - occupied);
  const isFull = available === 0;

  return L.divIcon({
    className: 'custom-ios-shelter-marker-frame',
    html: `
      <div class="ios-shelter-marker ${isFull ? 'full' : 'available'}">
        <span class="shelter-icon-emoji">🏠</span>
        <span class="shelter-badge-capacity">${occupied}/${capacity}</span>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17]
  });
};

const createClusterMarkerIcon = (incident) => {
  const isVerified = incident.status === 'verified';
  const isAutoVerified = incident.is_auto_verified || (isVerified && incident.report_count >= 5);
  const markerClass = isVerified ? 'ios-verified-cluster-marker' : 'ios-pending-cluster-marker';
  const emojiMap = {
    'mud_crack': '⚡',
    'stream_overflow': '🌊',
    'rockfall': '🪨',
    'blocked_road': '🚧',
    'slope_movement': '⛰️'
  };
  const emoji = emojiMap[incident.primary_hazard_type] || '⚠️';
  const badgeText = isAutoVerified ? `✓ ${incident.report_count}` : isVerified ? 'VERIFIED' : `${incident.report_count}`;

  return L.divIcon({
    className: 'custom-ios-cluster-marker-frame',
    html: `
      <div class="${markerClass}">
        <span class="cluster-emoji">${emoji}</span>
        <span class="cluster-badge-count ${isAutoVerified ? 'auto-verified' : ''}">${badgeText}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16]
  });
};

function IosSwitch({ checked, onChange, label }) {
  return (
    <div className="ios-switch-wrapper" onClick={() => onChange(!checked)}>
      <div className={`ios-switch-bg ${checked ? 'active' : ''}`}>
        <div className="ios-switch-thumb" />
      </div>
      {label && <span style={{ fontSize: '11px', fontWeight: '550', color: 'var(--text-primary)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>{label}</span>}
    </div>
  );
}

function MapClickInterceptor({ pinDropModeRef, onPinDrop, onSelectNode, proximityScope }) {
  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng;

      // If in Pin Drop Mode (Phase 3), open hazard report modal
      if (pinDropModeRef.current) {
        onPinDrop({ lat, lng });
        return;
      }

      // If in "Near Me" (local) mode, do NOT switch to All Kerala and do NOT mark custom nodes.
      // Target node inspection and custom sector marking are strictly reserved for "All Kerala" mode.
      if (proximityScope !== 'state') {
        return;
      }

      // Standard Topography Inspection (Target Node Selection in All Kerala mode only)
      const { elevation: approxElev, slope: calculatedSlope, soil: soilType } = resolveKeralaTopography(lat, lng);

      const freshNode = {
        id: `Sector Grid Box (${lat.toFixed(3)}°N, ${lng.toFixed(3)}°E)`,
        displayName: "Resolving Topography...",
        lat: lat,
        lng: lng,
        slope: calculatedSlope,
        elevation: approxElev,
        soil: soilType,
        isLiveGps: false
      };

      onSelectNode(freshNode);
    },
  });
  return null;
}

// Geodetic Haversine Distance in Kilometers
function getHaversineDistanceKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return 9999;
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export default function App() {
  // Phase 2 Auth & Profile State
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('terrarisk_user');
    try { return saved ? JSON.parse(saved) : null; } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem('terrarisk_token') || '');
  const isAuthorityUser = Boolean(user && (user.role === 'Authority_Admin' || user.role === 'Admin'));

  const [toast, setToast] = useState({ show: false, message: '', type: 'info' });

  const triggerToast = useCallback((message, type = 'info') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast(prev => ({ ...prev, show: false })), 4000);
  }, []);

  const [selectedNode, setSelectedNode] = useState(KERALA_NODES[0]);
  const [simMode, setSimMode] = useState(false);
  const [showHotspots, setShowHotspots] = useState(!isAuthorityUser);
  const [showIncidents, setShowIncidents] = useState(!isAuthorityUser);
  const [showTelemetryNodes, setShowTelemetryNodes] = useState(false);
  const [hotspots, setHotspots] = useState(DEFAULT_HOTSPOTS);
  const [incidents, setIncidents] = useState([]);
  const [rainfall, setRainfall] = useState(150);
  const [saturation, setSaturation] = useState(60);
  const [riskData, setRiskData] = useState({ risk_percentage: 0, live_rainfall: 0, live_humidity: 50, alert_text: "", geo_name: "", true_elevation: 0 });
  const [forecastData, setForecastData] = useState([]);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [safetyReport, setSafetyReport] = useState(null);
  const [checkingSafety, setCheckingSafety] = useState(false);

  // Phase 3 Incident Reporting & Pin-Drop State
  const [pinDropMode, setPinDropMode] = useState(false);
  const [droppedPinCoords, setDroppedPinCoords] = useState(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  // Phase 4 Authority Triage Portal State
  const [isAuthorityPortalOpen, setIsAuthorityPortalOpen] = useState(false);

  // Phase 5 Geo-Fenced Emergency Broadcasts
  const [activeBroadcasts, setActiveBroadcasts] = useState([]);

  // Phase 6 Visual GIS & Simulation State
  const [baseLayer, setBaseLayer] = useState('satellite');
  const [showRadar, setShowRadar] = useState(false);
  const [radarTileUrl, setRadarTileUrl] = useState('');
  const [radarOpacity, setRadarOpacity] = useState(0.75);
  const [showHillshade, setShowHillshade] = useState(false);
  const [showSlopeMesh, setShowSlopeMesh] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(!isAuthorityUser);

  // Phase 7 Safe Evacuation Route Planner & Relief Directory State
  const [shelters, setShelters] = useState(DEFAULT_SHELTERS);
  const [showShelters, setShowShelters] = useState(!isAuthorityUser);
  const [activeRoutePlan, setActiveRoutePlan] = useState(null);
  const [planningRoute, setPlanningRoute] = useState(false);
  const [selectedShelter, setSelectedShelter] = useState(null);
  const [isShelterDetailOpen, setIsShelterDetailOpen] = useState(false);
  const [occupancyEditShelter, setOccupancyEditShelter] = useState(null);
  const [isOccupancyModalOpen, setIsOccupancyModalOpen] = useState(false);

  // Phase 8 Offline PWA Hardening
  const [isOnline, setIsOnline] = useState(() => (typeof navigator !== 'undefined' ? navigator.onLine : true));
  const [isHelplinesModalOpen, setIsHelplinesModalOpen] = useState(false);

  // Missing Persons SOS Board
  const [isMissingModalOpen, setIsMissingModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [showLocationPermissionPrompt, setShowLocationPermissionPrompt] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const mapRef = useRef(null);
  const simModeRef = useRef(simMode);
  const rainfallRef = useRef(rainfall);
  const saturationRef = useRef(saturation);
  const pinDropModeRef = useRef(pinDropMode);

  useEffect(() => { simModeRef.current = simMode; }, [simMode]);
  useEffect(() => { rainfallRef.current = rainfall; }, [rainfall]);
  useEffect(() => { saturationRef.current = saturation; }, [saturation]);
  useEffect(() => { pinDropModeRef.current = pinDropMode; }, [pinDropMode]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Phase 8: Online / Offline Network Status Listener
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      triggerToast("✓ Network connection restored. Live telemetry online.", "success");
    };
    const handleOffline = () => {
      setIsOnline(false);
      triggerToast("⚡ Offline Mode Active: Using cached disaster matrix & cellular protocols.", "info");
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [triggerToast]);

  // Hyper-Local Proximity Scope State: 'local' (30 km radius of user / GPS) vs 'state' (All Kerala)
  const [proximityScope, setProximityScope] = useState(() => (!user || user.role !== 'Authority_Admin' ? 'local' : 'state'));
  const [deviceCoords, setDeviceCoords] = useState(null);
  const [isLocatingDevice, setIsLocatingDevice] = useState(false);

  // Request Live Device GPS Geolocation Permission & Synchronize Weather Forecast
  const requestDeviceLocation = useCallback((autoFly = true) => {
    if (!navigator.geolocation) {
      if (autoFly) setShowLocationPermissionPrompt(true);
      triggerToast("Geolocation is not supported by your browser.", "warning");
      return;
    }
    setIsLocatingDevice(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = parseFloat(pos.coords.latitude.toFixed(4));
        const lng = parseFloat(pos.coords.longitude.toFixed(4));
        const accuracy = Math.round(pos.coords.accuracy || 15);

        const locObj = { lat, lng, accuracy, label: 'Live GPS Location' };
        setDeviceCoords(locObj);
        setProximityScope('local');
        setIsLocatingDevice(false);
        setShowLocationPermissionPrompt(false);

        // Calculate localized topography for current coordinates
        const { elevation: approxElev, slope: calculatedSlope, soil: soilType } = resolveKeralaTopography(lat, lng);

        // Synchronize selected node so risk prediction and weather forecast update to current location
        setSelectedNode({
          id: `Live GPS Sector (${lat.toFixed(3)}°N, ${lng.toFixed(3)}°E)`,
          displayName: `Live Location (${lat.toFixed(2)}°, ${lng.toFixed(2)}°)`,
          lat: lat,
          lng: lng,
          slope: calculatedSlope,
          elevation: approxElev,
          soil: soilType,
          isLiveGps: true
        });

        if (autoFly && mapRef.current) {
          mapRef.current.flyTo([lat, lng], 13, { animate: true, duration: 1.2 });
        }
        triggerToast(`📍 Live Location Active: [${lat}°N, ${lng}°E]. Weather & hazard metrics synced.`, "success");
      },
      (err) => {
        setIsLocatingDevice(false);
        console.log("Device geolocation error or permission dismissed:", err.message);
        if (autoFly) {
          setShowLocationPermissionPrompt(true);
          triggerToast("Location access required. Please enable location in system settings.", "warning");
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }, [triggerToast]);

  // Prompt device location permission on initial mount for citizen/public users
  useEffect(() => {
    if (navigator.geolocation && (!user || user.role !== 'Authority_Admin')) {
      const timer = setTimeout(() => {
        requestDeviceLocation(false);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [user, requestDeviceLocation]);

  // Role-Based Smart Map Discovery: Auto-enable vital safety layers for Citizens & Public visitors,
  // while preserving a clean tactical canvas for Authority Admins.
  useEffect(() => {
    const isAdmin = Boolean(user && (user.role === 'Authority_Admin' || user.role === 'Admin'));
    const timer = setTimeout(() => {
      setShowShelters(!isAdmin);
      setShowIncidents(!isAdmin);
      setShowHotspots(!isAdmin);
      setShowHeatmap(!isAdmin);
      setProximityScope(isAdmin ? 'state' : 'local');
    }, 0);
    return () => clearTimeout(timer);
  }, [user]);

  // Current user's focus anchor for hyper-local filtering (Prioritizes Live GPS -> Selected Node in All Kerala)
  const userFocusCoords = useMemo(() => {
    if (deviceCoords) {
      return { lat: deviceCoords.lat, lng: deviceCoords.lng, label: 'Live GPS', isLiveGps: true, accuracy: deviceCoords.accuracy };
    }
    if (proximityScope === 'state' && selectedNode?.lat && selectedNode?.lng) {
      return { lat: selectedNode.lat, lng: selectedNode.lng, label: selectedNode.displayName || selectedNode.id.split(' (')[0], isLiveGps: false };
    }
    return { lat: 10.5, lng: 76.2, label: 'Live Location', isLiveGps: false };
  }, [deviceCoords, selectedNode, proximityScope]);

  // Auto-Fly Map to User Home GPS on acquisition (only when device location is actively acquired)
  useEffect(() => {
    if (deviceCoords && mapRef.current && proximityScope === 'local') {
      mapRef.current.flyTo([deviceCoords.lat, deviceCoords.lng], 13, { animate: true, duration: 1.2 });
    }
  }, [deviceCoords, proximityScope]);

  // Filtered Datasets: Only show hazards, shelters, and hotspots relevant to user when in 'local' scope
  const displayedIncidents = useMemo(() => {
    const list = Array.isArray(incidents) ? incidents : [];
    if (proximityScope === 'state' || !userFocusCoords) return list;
    return list.filter(inc => inc && !isNaN(inc.lat) && !isNaN(inc.lng) && getHaversineDistanceKm(userFocusCoords.lat, userFocusCoords.lng, inc.lat, inc.lng) <= 30.0);
  }, [incidents, proximityScope, userFocusCoords]);

  const displayedShelters = useMemo(() => {
    const list = Array.isArray(shelters) ? shelters : [];
    if (proximityScope === 'state' || !userFocusCoords) return list;
    return list.filter(s => s && !isNaN(s.lat) && !isNaN(s.lng) && getHaversineDistanceKm(userFocusCoords.lat, userFocusCoords.lng, s.lat, s.lng) <= 35.0);
  }, [shelters, proximityScope, userFocusCoords]);

  const displayedHotspots = useMemo(() => {
    const list = Array.isArray(hotspots) ? hotspots : [];
    if (proximityScope === 'state' || !userFocusCoords) return list;
    return list.filter(h => h && !isNaN(h.lat) && !isNaN(h.lng) && getHaversineDistanceKm(userFocusCoords.lat, userFocusCoords.lng, h.lat, h.lng) <= 30.0);
  }, [hotspots, proximityScope, userFocusCoords]);

  // Dynamic Real-Time Landslide & Hazard Heatmap Kernel Density Points
  const heatmapPoints = useMemo(() => {
    const pts = [];
    const localRadius = proximityScope === 'local' ? 35.0 : 9999.0;
    const listInc = Array.isArray(incidents) ? incidents : [];
    const listHot = Array.isArray(hotspots) ? hotspots : [];

    // 1. Live Incidents & Clustered Reports
    listInc.forEach(inc => {
      if (inc && !isNaN(inc.lat) && !isNaN(inc.lng) && userFocusCoords && getHaversineDistanceKm(userFocusCoords.lat, userFocusCoords.lng, inc.lat, inc.lng) <= localRadius) {
        const weight = Math.min(1.0, Math.max(0.3, (inc.avg_severity || 3) / 5.0));
        pts.push([inc.lat, inc.lng, weight]);
      }
    });
    // 2. High-Risk Steep Western Ghats Escarpments (>22°) Scaled by Live Rainfall & Saturation
    const rainFactor = Math.min(1.0, Math.max(0.15, (rainfall / 260.0) * (saturation / 80.0)));
    KERALA_NODES.filter(n => n.slope >= 22).forEach(n => {
      if (userFocusCoords && getHaversineDistanceKm(userFocusCoords.lat, userFocusCoords.lng, n.lat, n.lng) <= localRadius) {
        const slopeWeight = Math.min(1.0, (n.slope / 45.0) * rainFactor);
        pts.push([n.lat, n.lng, slopeWeight]);
      }
    });
    // 3. Historic Landslide Inventory Hotspots
    listHot.forEach(h => {
      if (h && !isNaN(h.lat) && !isNaN(h.lng) && userFocusCoords && getHaversineDistanceKm(userFocusCoords.lat, userFocusCoords.lng, h.lat, h.lng) <= localRadius) {
        pts.push([h.lat, h.lng, 0.45 * rainFactor]);
      }
    });
    return pts;
  }, [incidents, hotspots, rainfall, saturation, proximityScope, userFocusCoords]);

  // Load hotspots
  useEffect(() => {
    api.get('/api/hotspots')
      .then(res => {
        if (Array.isArray(res.data)) {
          setHotspots(res.data);
        } else if (res.data && Array.isArray(res.data.hotspots)) {
          setHotspots(res.data.hotspots);
        }
      })
      .catch(() => console.log("System data arrays synced."));
  }, []);

  // Fetch active incidents (Phase 3)
  const fetchActiveIncidents = () => {
    api.get('/api/incidents/active')
      .then(res => {
        if (res.data && res.data.success && Array.isArray(res.data.incidents)) {
          setIncidents(res.data.incidents);
        }
      })
      .catch(() => console.log("Incidents sync gap."));
  };

  // Authority 1-Tap Incident Resolution from Map
  const handleResolveClusterFromMap = async (clusterId, e) => {
    if (e) e.stopPropagation();
    try {
      const res = await api.post('/api/incidents/resolve', {
        cluster_id: clusterId,
        notes: "Site rectified & cleared from live map by Authority Admin."
      });
      if (res.data.success) {
        triggerToast("✓ Hazard rectified & cleared. Marker removed from live map.", "success");
        fetchActiveIncidents();
      } else {
        triggerToast(res.data.error || "Failed to resolve hazard.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Error resolving hazard.", "error");
    }
  };

  // Fetch active emergency broadcasts (Phase 5)
  const fetchActiveBroadcasts = () => {
    api.get('/api/alerts/active-broadcasts')
      .then(res => {
        if (res.data && res.data.success && Array.isArray(res.data.broadcasts)) {
          setActiveBroadcasts(res.data.broadcasts);
        }
      })
      .catch(() => console.log("Broadcasts sync gap."));
  };

  // Fetch relief shelters (Phase 7)
  const fetchShelters = () => {
    api.get('/api/shelters')
      .then(res => {
        if (res.data && res.data.success && Array.isArray(res.data.shelters)) {
          setShelters(res.data.shelters);
        }
      })
      .catch(() => console.log("Shelters sync gap."));
  };

  useEffect(() => {
    fetchActiveIncidents();
    fetchActiveBroadcasts();
    fetchShelters();
    const interval = setInterval(() => {
      fetchActiveIncidents();
      fetchActiveBroadcasts();
      fetchShelters();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Phase 7 Evacuation Route Planner
  const handlePlanEvacuationRoute = async (targetShelter = null) => {
    const startLat = deviceCoords?.lat || selectedNode?.lat || 11.5542;
    const startLng = deviceCoords?.lng || selectedNode?.lng || 76.1308;

    setPlanningRoute(true);
    triggerToast("Calculating safest hazard-avoiding evacuation corridor...", "info");

    try {
      const res = await api.post('/api/routes/evacuate', {
        start_lat: startLat,
        start_lng: startLng,
        destination_shelter_id: targetShelter?.id
      });

      if (res.data.success) {
        setActiveRoutePlan(res.data);
        const dest = res.data.destination_shelter;
        triggerToast(`✓ Safe route generated to ${dest.name}! (${res.data.total_distance_km} km • ${res.data.estimated_time_mins} mins ETA)`, "success");
      } else {
        triggerToast(res.data.error || "Could not calculate evacuation route.", "error");
      }
    } catch {
      triggerToast("Evacuation routing service connection error.", "error");
    } finally {
      setPlanningRoute(false);
    }
  };

  const handleLogout = useCallback(() => {
    setToken('');
    setUser(null);
    setSafetyReport(null);
    localStorage.removeItem('terrarisk_token');
    localStorage.removeItem('terrarisk_user');
    triggerToast('Logged out of TerraRisk session.', 'info');
  }, [triggerToast]);

  // Verify auth session on mount
  useEffect(() => {
    if (token) {
      api.get('/api/auth/me')
        .then(res => {
          if (res.data.success) {
            setUser(res.data.user);
            localStorage.setItem('terrarisk_user', JSON.stringify(res.data.user));
          }
        })
        .catch(() => {
          console.log("Session expired or invalid token.");
          handleLogout();
        });
    }
  }, [token, handleLogout]);

  const handleAuthSuccess = (newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('terrarisk_token', newToken);
    localStorage.setItem('terrarisk_user', JSON.stringify(newUser));

    // When citizen or volunteer logs in, immediately request live GPS coordinates to sync map and weather forecast
    if (newUser && newUser.role !== 'Authority_Admin') {
      setTimeout(() => {
        requestDeviceLocation(true);
      }, 100);
    }
  };

  const transmitTelemetry = (nodeObj, currentSimMode, currentRain, currentSat) => {
    api.post('/api/predict', {
      lat: nodeObj.lat,
      lng: nodeObj.lng,
      slope: nodeObj.slope,
      elevation: nodeObj.elevation,
      soil: nodeObj.soil,
      sim_mode: currentSimMode,
      manual_rainfall: parseFloat(currentRain),
      manual_saturation: parseFloat(currentSat)
    })
      .then(res => {
        setRiskData(res.data);
        if (res.data.true_elevation !== undefined) {
          setSelectedNode(prev => ({
            ...prev,
            elevation: res.data.true_elevation,
            slope: res.data.slope !== undefined ? res.data.slope : prev.slope,
            soil: res.data.soil !== undefined ? res.data.soil : prev.soil
          }));
        }
        if (res.data.geo_name && (nodeObj.id.startsWith("Sector Grid Box") || nodeObj.id.startsWith("Live") || nodeObj.id.startsWith("Current") || nodeObj.id.startsWith("User"))) {
          setSelectedNode(prev => ({ ...prev, displayName: res.data.geo_name }));
        }
      })
      .catch(() => console.log("Matrix execution error."));

    api.post('/api/forecast', { lat: nodeObj.lat, lng: nodeObj.lng })
      .then(res => {
        if (res.data.success) setForecastData(res.data.forecast);
      })
      .catch(() => console.log("Forecast sync gap."));
  };

  // Active evaluation node:
  // In 'local' (Near Me) mode: Target node locking is disabled. Uses Live GPS if active or a neutral baseline.
  // In 'state' (All Kerala) mode: Target node system is active. Uses selectedNode.
  const activeEvalNode = useMemo(() => {
    if (proximityScope === 'local') {
      if (deviceCoords) {
        const { elevation: approxElev, slope: calculatedSlope, soil: soilType } = resolveKeralaTopography(deviceCoords.lat, deviceCoords.lng);
        return {
          id: `Live GPS Sector (${deviceCoords.lat.toFixed(3)}°N, ${deviceCoords.lng.toFixed(3)}°E)`,
          displayName: `Live Location (${deviceCoords.lat.toFixed(2)}°, ${deviceCoords.lng.toFixed(2)}°)`,
          lat: deviceCoords.lat,
          lng: deviceCoords.lng,
          slope: calculatedSlope,
          elevation: approxElev,
          soil: soilType,
          isLiveGps: true
        };
      }
      return {
        id: 'Near Me Area',
        displayName: 'Live Location (Acquiring GPS...)',
        lat: 10.5,
        lng: 76.2,
        slope: 5.0,
        elevation: 50,
        soil: 2,
        isLiveGps: false
      };
    }
    return selectedNode || KERALA_NODES[0];
  }, [proximityScope, deviceCoords, selectedNode]);

  useEffect(() => {
    transmitTelemetry(activeEvalNode, simMode, rainfall, saturation);
  }, [activeEvalNode, simMode, rainfall, saturation]);

  // Phase 2: Check My Area Action
  const handleCheckMyArea = async () => {
    if (!token || !user) {
      setIsAuthModalOpen(true);
      return;
    }

    const currentLat = deviceCoords?.lat || selectedNode?.lat || 11.5542;
    const currentLng = deviceCoords?.lng || selectedNode?.lng || 76.1308;
    const label = deviceCoords ? 'Live GPS Location' : (selectedNode?.displayName || 'Current Sector');

    setCheckingSafety(true);
    triggerToast(`Evaluating real-time hazard status for ${label}...`, 'info');

    try {
      const res = await api.get(`/api/user/check-safety?lat=${currentLat}&lng=${currentLng}`);
      if (res.data.success) {
        setSafetyReport(res.data);
        const statusType = res.data.status === 'Critical' ? 'error' : res.data.status === 'Advisory' ? 'info' : 'success';
        triggerToast(`Safety Report: ${res.data.status.toUpperCase()} level confirmed.`, statusType);
      }
    } catch {
      triggerToast('Could not complete safety check. Check connection.', 'error');
    } finally {
      setCheckingSafety(false);
    }
  };

  // Phase 3: Initiate Report Hazard Mode
  const handleStartReportHazard = () => {
    if (!token || !user) {
      setIsAuthModalOpen(true);
      triggerToast('Please sign in with your citizen/volunteer profile to report hazards.', 'info');
      return;
    }
    setPinDropMode(true);
    triggerToast('📍 Pin-Drop Mode Active: Click anywhere on the map to mark the hazard.', 'info');
  };

  // Phase 4: Open Authority Command Suite
  const handleOpenAuthoritySuite = async () => {
    if (token && user && (user.role === 'Authority_Admin' || user.role === 'Volunteer')) {
      setIsAuthorityPortalOpen(true);
      return;
    }

    if (!user) {
      setIsAuthModalOpen(true);
      triggerToast("Please sign in with your Authority Officer or Volunteer account.", "info");
      return;
    }

    // Standard Citizen attempted to access command suite
    triggerToast("Access Restricted: Command Center is restricted to KSDMA Disaster Officers & Volunteers.", "warning");
  };

  const dominantWeather = forecastData[0]?.condition || "clear";
  let weatherThemeClass = "weather-theme-clear";
  if (dominantWeather === "rain") weatherThemeClass = "weather-theme-rain";
  else if (dominantWeather === "thunderstorm") weatherThemeClass = "weather-theme-thunder";
  else if (dominantWeather === "clouds") weatherThemeClass = "weather-theme-clouds";

  const renderWeatherIcon = (cond) => {
    switch (cond) {
      case 'rain': return <CloudRain size={18} className="weather-animated-icon color-rain" />;
      case 'thunderstorm': return <CloudLightning size={18} className="weather-animated-icon color-thunder" />;
      case 'clouds': return <Cloud size={18} className="weather-animated-icon color-cloud" />;
      default: return <Sun size={18} className="weather-animated-icon color-sun" />;
    }
  };

  const risk = riskData.risk_percentage || 0;
  const isGuardActive = activeEvalNode.slope < 8.0 && activeEvalNode.elevation < 150.0;
  const gaugeColor = isGuardActive ? 'var(--accent-green)' : risk >= 85 ? 'var(--accent-red)' : risk >= 50 ? 'var(--accent-orange)' : 'var(--accent-green)';
  const circumference = 2 * Math.PI * 44;
  const strokeDashoffset = circumference - (risk / 100) * circumference;
  const displayLabel = activeEvalNode.displayName || activeEvalNode.id;
  const currentRainInt = simMode ? rainfall : (riskData.live_rainfall || 0);

  // Check if the current selected node corresponds to the live device GPS position
  const isSelectedAtLiveGps = Boolean(
    deviceCoords && activeEvalNode && (
      activeEvalNode.isLiveGps ||
      (Math.abs(activeEvalNode.lat - deviceCoords.lat) < 0.0001 && Math.abs(activeEvalNode.lng - deviceCoords.lng) < 0.0001)
    )
  );

  const globalAppLayoutClass = theme === 'light' ? `global-bg-${dominantWeather}` : '';

  return (
    <div className={`app-main-viewport-frame ${globalAppLayoutClass}`} style={{ minHeight: '100vh', paddingBottom: '40px', position: 'relative', overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', top: '10%', left: '5%', width: '350px', height: '350px', borderRadius: '50%', background: theme === 'dark' ? 'radial-gradient(circle, rgba(10, 132, 255, 0.08) 0%, rgba(10, 132, 255, 0) 70%)' : 'radial-gradient(circle, rgba(10, 132, 255, 0.03) 0%, rgba(10, 132, 255, 0) 70%)', filter: 'blur(80px)', zIndex: -1, pointerEvents: 'none' }} />

      {/* Top Navigation Bar with Minimalist Brand & Left Drawer Trigger */}
      <header className="ios-glass header-nav-bar minimalist-header">
        <div className="header-left-cluster">
          <button
            className="btn-menu-drawer-toggle"
            onClick={() => setIsSidebarOpen(true)}
            title="Open Disaster Command Menu"
          >
            <Menu size={18} />
            <span className="btn-menu-label">Menu</span>
          </button>

          <div className="header-brand-box">
            <div className="brand-logo-badge">
              <span className="brand-pulse-dot" />
              <h1 className="header-brand-title">TERRARISK <span className="brand-accent">AI</span></h1>
            </div>
            <p className="header-brand-subtitle">KERALA DISASTER COMMAND MATRIX</p>
          </div>
        </div>

        {/* Right Area: System Status & User Profile Trigger */}
        {/* Right Area: System Status, Citizen Location Trigger & User Profile */}
        <div className="header-right-cluster">
          {/* Citizen Location Access Quick Button */}
          {user && user.role === 'Citizen' && (
            <button
              type="button"
              className={`header-location-btn ${deviceCoords ? 'active-locked' : ''} ${isLocatingDevice ? 'locating' : ''}`}
              onClick={() => requestDeviceLocation(true)}
              disabled={isLocatingDevice}
              title={
                deviceCoords
                  ? `Live GPS Active: [${deviceCoords.lat}°N, ${deviceCoords.lng}°E] (±${deviceCoords.accuracy}m). Click to focus map on your live position.`
                  : "Enable live GPS location access to find your exact location on the map"
              }
            >
              <div className="header-loc-icon-wrap">
                <Navigation
                  size={14}
                  className={isLocatingDevice ? 'spin-anim' : ''}
                  color={deviceCoords ? '#30D158' : '#38BDF8'}
                />
                {deviceCoords && <span className="header-loc-pulse" />}
              </div>
              <span className="header-loc-text">
                {isLocatingDevice ? 'Locating...' : deviceCoords ? 'Live GPS Active' : 'My Location'}
              </span>
            </button>
          )}

          <div className="header-status-pill">
            <span className="status-indicator-dot" />
            <span className="status-indicator-text">Matrix Active</span>
          </div>

          {user ? (
            <div className="header-user-badge-minimal" onClick={() => setIsSidebarOpen(true)} title="View Profile & Settings">
              <div className="user-mini-avatar">{user.name.charAt(0).toUpperCase()}</div>
              <span className="user-minimal-name">{user.name.split(' ')[0]}</span>
              <span className={`user-role-tag ${user.role.toLowerCase()}`}>
                {user.role === 'Authority_Admin' ? 'ADMIN' : user.role === 'Volunteer' ? 'VOLUNTEER' : 'CITIZEN'}
              </span>
            </div>
          ) : (
            <button onClick={() => setIsAuthModalOpen(true)} className="nav-btn-signin">
              <User size={14} />
              <span>Sign In</span>
            </button>
          )}

          <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} className="nav-btn-theme" title="Toggle Theme">
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
          </button>
        </div>
      </header>

      {/* Left-Side Slider / Command Drawer */}
      <LeftSidebarDrawer
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onOpenSafeRoute={() => handlePlanEvacuationRoute()}
        onOpenReportHazard={handleStartReportHazard}
        onOpenMissingPersons={() => setIsMissingModalOpen(true)}
        onOpenAuthoritySuite={handleOpenAuthoritySuite}
        onOpenSettings={() => setIsSettingsModalOpen(true)}
        onOpenHelplines={() => setIsHelplinesModalOpen(true)}
        onCheckMyArea={handleCheckMyArea}
        checkingSafety={checkingSafety}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
        theme={theme}
        setTheme={setTheme}
        planningRoute={planningRoute}
        pinDropMode={pinDropMode}
      />

      <div className="app-container">
        {/* Phase 8: Offline Mode Warning Banner */}
        {!isOnline && (
          <div className="offline-mode-indicator-strip ios-glass">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <WifiOff size={15} color="#F59E0B" className="bounce-anim" />
              <span style={{ fontSize: '12px', fontWeight: '550', color: 'var(--text-primary)' }}>
                OFFLINE MODE ACTIVE: Operating on cached relief camps and emergency protocols. Voice helplines remain fully active.
              </span>
            </div>
            <button onClick={() => setIsHelplinesModalOpen(true)} className="offline-helpline-quick-btn">
              <PhoneCall size={12} /> Helplines Directory
            </button>
          </div>
        )}

        {/* Phase 5: Public Flashing Geo-Fenced Red Emergency Broadcast Banner */}
        <BroadcastAlertBanner
          broadcasts={activeBroadcasts}
          currentCoords={deviceCoords || selectedNode}
          onFocusAlert={(bcast) => {
            setSelectedNode({
              id: `Alert Epicenter (${bcast.lat.toFixed(3)}°N, ${bcast.lng.toFixed(3)}°E)`,
              displayName: `Hazard Epicenter (${bcast.hazard_type?.replace('_', ' ') || 'Geohazard'})`,
              lat: bcast.lat,
              lng: bcast.lng,
              slope: 35.0,
              elevation: 900,
              soil: 1
            });
            setProximityScope('state');
            triggerToast(`Map focused on active warning perimeter (${bcast.radius_km}km radius). Target node active.`, 'info');
          }}
          onFindShelter={() => handlePlanEvacuationRoute()}
        />

        {/* Phase 2: Localized Citizen Safety Status Banner */}
        {safetyReport && (
          <SafetyBanner
            safetyData={safetyReport}
            user={user}
            onClose={() => setSafetyReport(null)}
            onFocusLocation={() => {
              const currentLat = deviceCoords?.lat || selectedNode?.lat || 11.5542;
              const currentLng = deviceCoords?.lng || selectedNode?.lng || 76.1308;
              if (mapRef.current) {
                mapRef.current.flyTo([currentLat, currentLng], 13, { animate: true, duration: 1.2 });
              }
            }}
          />
        )}

        {/* Atmospheric Forecast Array (Compact Top HUD above Map) */}
        <div className={`ios-card weather-hud-strip-wrapper ${weatherThemeClass}`}>
          <div className="weather-hud-info-header">
            <span className="weather-hud-badge">Atmospheric Forecast Array</span>
            <span className="weather-location-text">{displayLabel.split(' (')[0]}</span>
          </div>
          <div className="weather-forecast-days-grid">
            {forecastData.length > 0 ? (
              forecastData.map((f, i) => (
                <div key={i} className="forecast-day-column-tile">
                  <span className="forecast-day-name">{i === 0 ? "Today" : f.day}</span>
                  <div className="forecast-icon-frame">{renderWeatherIcon(f.condition)}</div>
                  <span className="forecast-temp-val">{f.temp}°C</span>
                  <span className="forecast-desc-text">{f.desc}</span>
                  <span className="forecast-humidity-text">💧 {f.humidity}% sat</span>
                </div>
              ))
            ) : (
              <div className="weather-loading-fallback">Awaiting network coordinate validation loop...</div>
            )}
          </div>
        </div>

        {/* Leaflet Interactive Map & GIS Overlay Container */}
        <div className={`ios-card map-outer-wrapper ${pinDropMode ? 'pin-drop-active-cursor' : ''}`} style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', height: '580px', width: '100%', zIndex: 10, marginBottom: '16px' }}>
          {/* Phase 3 Pin-Drop Floating Prompt */}
          {pinDropMode && (
            <div className="map-pin-drop-banner ios-glass">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MapPin size={16} color="var(--accent)" className="bounce-anim" />
                <span style={{ fontSize: '12px', fontWeight: '550', color: 'var(--text-primary)' }}>
                  PIN-DROP MODE ACTIVE: Click anywhere on the map to pinpoint hazard coordinates
                </span>
              </div>
              <button onClick={() => setPinDropMode(false)} className="pin-drop-cancel-btn">
                <X size={14} /> Cancel
              </button>
            </div>
          )}

          {/* Phase 7: Live Turn-by-Turn Safe Evacuation Guidance HUD */}
          <EvacuationGuidanceCard
            routePlan={activeRoutePlan}
            onClose={() => setActiveRoutePlan(null)}
            onFocusShelter={(dest) => {
              setSelectedNode({
                id: `Shelter (${dest.name})`,
                displayName: `${dest.name} (${dest.district})`,
                lat: dest.lat,
                lng: dest.lng,
                slope: 15.0,
                elevation: 500,
                soil: 1
              });
              setProximityScope('state');
              triggerToast(`Focused on ${dest.name}. Target node active.`, 'info');
            }}
          />

          {/* Phase 6: Live RainViewer Doppler Radar Player Bar */}
          <RadarTimelinePlayer
            isVisible={showRadar}
            onFrameChange={(url) => setRadarTileUrl(url)}
          />

          {/* Phase 6: Floating GIS Layers Control Console */}
          <MapLayersControl
            baseLayer={baseLayer}
            onBaseLayerChange={setBaseLayer}
            showRadar={showRadar}
            onToggleRadar={setShowRadar}
            radarOpacity={radarOpacity}
            onRadarOpacityChange={setRadarOpacity}
            showHillshade={showHillshade}
            onToggleHillshade={setShowHillshade}
            showSlopeMesh={showSlopeMesh}
            onToggleSlopeMesh={setShowSlopeMesh}
            showHeatmap={showHeatmap}
            onToggleHeatmap={setShowHeatmap}
            showIncidents={showIncidents}
            onToggleIncidents={setShowIncidents}
            showHotspots={showHotspots}
            onToggleHotspots={setShowHotspots}
            showShelters={showShelters}
            onToggleShelters={setShowShelters}
            showTelemetryNodes={showTelemetryNodes}
            onToggleTelemetryNodes={setShowTelemetryNodes}
          />

          {/* Phase 6: Floating Terrain & Slope Legend */}
          <TerrainSlopeLegend />

          {/* Hyper-Local Proximity Scope Toggle Capsule */}
          <div className="proximity-scope-bar-wrapper">
            <div className="proximity-scope-capsule ios-glass">
              <button
                type="button"
                className={`scope-pill-btn ${proximityScope === 'local' ? 'active' : ''}`}
                onClick={() => {
                  setProximityScope('local');
                  if (deviceCoords) {
                    if (mapRef.current) {
                      mapRef.current.flyTo([deviceCoords.lat, deviceCoords.lng], 13, { animate: true, duration: 1.0 });
                    }
                    triggerToast('📍 Near Me Active: Filtered to live GPS safety zone (30km).', 'info');
                  } else {
                    requestDeviceLocation(true);
                  }
                }}
                title="Filter map to only show hazards, shelters, and risk within 30 km of your location"
              >
                <MapPin size={13} color={proximityScope === 'local' ? '#38BDF8' : 'var(--text-secondary)'} />
                <span>Near Me {deviceCoords ? '(Live GPS)' : ''}</span>
                {proximityScope === 'local' && <span className="scope-active-dot" />}
              </button>

              <button
                type="button"
                className={`scope-pill-btn ${proximityScope === 'state' ? 'active' : ''}`}
                onClick={() => {
                  setProximityScope('state');
                  if (mapRef.current) {
                    mapRef.current.flyTo([selectedNode?.lat || 10.5, selectedNode?.lng || 76.2], 8.5, { animate: true, duration: 1.0 });
                  }
                  triggerToast('🌐 All Kerala active: Target node inspection system enabled. Click anywhere to inspect sectors.', 'info');
                }}
                title="View all hazards and shelters across Kerala with target node inspection"
              >
                <Compass size={13} color={proximityScope === 'state' ? 'var(--accent)' : 'var(--text-secondary)'} />
                <span>All Kerala</span>
              </button>
            </div>
          </div>

          {/* Dedicated Modern GPS Floating Action Button on Map */}
          <div className="map-gps-fab-container">
            <button
              type="button"
              className={`map-gps-fab ios-glass ${deviceCoords ? 'gps-locked' : ''} ${isLocatingDevice ? 'locating' : ''}`}
              onClick={() => requestDeviceLocation(true)}
              disabled={isLocatingDevice}
              title={deviceCoords ? `Live GPS Locked: [${deviceCoords.lat}°N, ${deviceCoords.lng}°E] (±${deviceCoords.accuracy}m). Click to center map.` : "Acquire Live GPS Device Location"}
            >
              <div className="gps-fab-icon-wrap">
                <Navigation
                  size={16}
                  className={isLocatingDevice ? 'spin-anim' : ''}
                  color={deviceCoords ? '#30D158' : '#38BDF8'}
                />
                {deviceCoords && <span className="gps-fab-live-ping" />}
              </div>
              <span className="gps-fab-label">
                {isLocatingDevice ? 'Acquiring GPS...' : deviceCoords ? `GPS Live (±${deviceCoords.accuracy}m)` : 'Locate Me'}
              </span>
            </button>
          </div>

          <MapContainer ref={mapRef} attributionControl={false} center={[11.25, 75.8]} zoom={9} minZoom={7.5} maxBounds={KERALA_BOUNDS} maxBoundsViscosity={1.0} style={{ height: '100%', width: '100%' }}>
            {/* Phase 9: Dynamic Automated Risk Heatmap (Kernel Density) */}
            <HazardHeatmapLayer points={heatmapPoints} isVisible={showHeatmap} />

            {/* Phase 6: Dynamic Base Layer Tile */}
            <TileLayer
              key={`base_${baseLayer}`}
              url={BASE_LAYERS[baseLayer]?.url || BASE_LAYERS.satellite.url}
              attribution={BASE_LAYERS[baseLayer]?.attribution || BASE_LAYERS.satellite.attribution}
            />
            <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png" zIndex={20} />

            {/* Phase 6: 3D Hillshade Terrain Relief Layer */}
            {showHillshade && (
              <TileLayer
                url={HILLSHADE_LAYER_URL}
                opacity={0.45}
                zIndex={5}
              />
            )}

            {/* Phase 6: Live RainViewer Doppler Radar Overlay */}
            {showRadar && radarTileUrl && (
              <TileLayer
                key={`radar_${radarTileUrl}`}
                url={radarTileUrl}
                opacity={radarOpacity}
                zIndex={15}
              />
            )}

            {/* Phase 7: Safe Hazard-Avoidance Evacuation Polyline */}
            {activeRoutePlan && activeRoutePlan.route_polyline && (
              <>
                {/* Outer Glow Halo */}
                <Polyline
                  positions={activeRoutePlan.route_polyline}
                  pathOptions={{ color: '#0284C7', weight: 8, opacity: 0.35, lineCap: 'round' }}
                />
                {/* Foreground Route Line */}
                <Polyline
                  positions={activeRoutePlan.route_polyline}
                  pathOptions={{ color: '#38BDF8', weight: 4.5, opacity: 0.95, dashArray: '8, 6' }}
                />
                {/* Origin Circle Ring */}
                <Circle
                  center={[activeRoutePlan.start.lat, activeRoutePlan.start.lng]}
                  radius={350}
                  pathOptions={{ color: '#38BDF8', fillColor: '#38BDF8', fillOpacity: 0.8 }}
                />
                {/* Destination Shelter Circle Ring */}
                <Circle
                  center={[activeRoutePlan.destination_shelter.lat, activeRoutePlan.destination_shelter.lng]}
                  radius={450}
                  pathOptions={{ color: '#30D158', fillColor: '#30D158', fillOpacity: 0.8 }}
                />
                {/* Avoided Hazard Warning Rings */}
                {activeRoutePlan.avoided_hazards?.map((h, i) => (
                  <Circle
                    key={`avoided_hz_${i}`}
                    center={[h.lat, h.lng]}
                    radius={h.radius_km * 1000}
                    pathOptions={{ color: '#EF4444', fillColor: '#EF4444', fillOpacity: 0.12, dashArray: '4, 6' }}
                  />
                ))}
              </>
            )}

            {/* Phase 6: High-Risk Steep Slope Contours (>30°) */}
            {showSlopeMesh && (
              <>
                {KERALA_NODES.filter(n => n.slope >= 30).map((node, idx) => (
                  <Circle
                    key={`slope_mesh_${idx}`}
                    center={[node.lat, node.lng]}
                    radius={8000}
                    pathOptions={{
                      color: '#EF4444',
                      fillColor: '#EF4444',
                      fillOpacity: 0.16,
                      weight: 2,
                      dashArray: '4, 6'
                    }}
                  >
                    <Tooltip direction="top">
                      <span style={{ fontSize: '10.5px', fontWeight: '550', color: '#EF4444' }}>
                        ⚡ Steep Escarpment ({node.slope}&deg; Incline &bull; {node.elevation}m)
                      </span>
                    </Tooltip>
                  </Circle>
                ))}
              </>
            )}

            {/* Phase 7: Relief Shelters Directory Pins */}
            {showShelters && displayedShelters.map((shelter, i) => (
              <Marker
                key={`shelter_${shelter.id}_${i}`}
                position={[shelter.lat, shelter.lng]}
                icon={createShelterMarkerIcon(shelter)}
                eventHandlers={{
                  click: () => {
                    setSelectedShelter(shelter);
                    setIsShelterDetailOpen(true);
                  }
                }}
              >
                <Tooltip direction="top" offset={[0, -12]}>
                  <div style={{ padding: '2px 4px' }}>
                    <span style={{ fontWeight: '600', fontSize: '11px', color: 'var(--text-primary)' }}>{shelter.name}</span>
                    <div style={{ fontSize: '10px', color: 'var(--accent-green)', fontWeight: '500' }}>
                      {shelter.occupied}/{shelter.capacity} Beds &bull; {shelter.available_spots ?? (shelter.capacity - shelter.occupied)} Available
                    </div>
                  </div>
                </Tooltip>
              </Marker>
            ))}

            {/* Active Selected Target Node Pin (Only rendered when All Kerala mode is selected) */}
            {selectedNode && proximityScope === 'state' && !isSelectedAtLiveGps && (
              <Marker position={[selectedNode.lat, selectedNode.lng]} icon={createMarkerIcon(true)}>
                <Tooltip permanent offset={[0, -5]}>
                  <div style={{ color: 'var(--accent)', fontSize: '11px', fontWeight: '550', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <MapPin size={10} /> {selectedNode.displayName || selectedNode.id.split(' (')[0]}
                  </div>
                </Tooltip>
              </Marker>
            )}

            {/* Static Telemetry Nodes Grid (Only enabled and selectable in All Kerala mode) */}
            {showTelemetryNodes && proximityScope === 'state' && KERALA_NODES.filter(n => n.id !== selectedNode?.id).map((node, i) => (
              <Marker key={`node_${i}`} position={[node.lat, node.lng]} icon={createMarkerIcon(false)} eventHandlers={{ click: () => setSelectedNode(node) }}>
                <Tooltip direction="top" offset={[0, -5]}>
                  <div style={{ color: 'var(--text-primary)', fontSize: '11px', fontWeight: '500' }}>{node.id.split(' (')[0]}</div>
                </Tooltip>
              </Marker>
            ))}

            {/* Historic Hotspots */}
            {showHotspots && displayedHotspots.map((spot, i) => (
              <Fragment key={i}>
                <Marker position={[spot.lat, spot.lng]} icon={createHotspotIcon()}>
                  <Tooltip direction="top"><span style={{ color: 'var(--text-primary)', fontWeight: '500', fontSize: '11px' }}>Historic: {spot.name}</span></Tooltip>
                </Marker>
                <Circle center={[spot.lat, spot.lng]} radius={10000} pathOptions={{ color: 'var(--accent-red)', fillColor: 'var(--accent-red)', fillOpacity: 0.03, weight: 1 }} />
              </Fragment>
            ))}

            {/* Phase 3: Active Incident Clusters & Verified Hazards */}
            {showIncidents && displayedIncidents.map((inc, i) => {
              const isVerified = inc.status === 'verified';
              const sevColor = inc.avg_severity >= 4 ? 'var(--accent-red)' : inc.avg_severity >= 3 ? 'var(--accent-orange)' : 'var(--accent-green)';
              return (
                <Marker key={`inc_${inc.cluster_id}_${i}`} position={[inc.lat, inc.lng]} icon={createClusterMarkerIcon(inc)}>
                  <Tooltip direction="top" offset={[0, -10]} opacity={0.98}>
                    <div className="incident-popup-card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span className="incident-popup-title">
                          {inc.primary_hazard_type.replace('_', ' ').toUpperCase()}
                        </span>
                        <span className={`incident-popup-badge ${isVerified ? (inc.is_auto_verified || inc.report_count >= 5 ? 'auto-verified' : 'verified') : 'pending'}`}>
                          {isVerified ? (inc.is_auto_verified || inc.report_count >= 5 ? '⚡ AUTO-VERIFIED' : '✓ VERIFIED') : 'PENDING CLUSTER'}
                        </span>
                      </div>
                      {(inc.is_auto_verified || (isVerified && inc.report_count >= 5)) && (
                        <div style={{ fontSize: '10px', color: '#10B981', fontWeight: '700', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span>✓ Crowd consensus: Auto-verified by {inc.report_count} field reports</span>
                        </div>
                      )}
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                        {inc.report_count} {inc.report_count === 1 ? 'citizen report' : 'reports clustered'} (within 500m)
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '550', color: sevColor, marginBottom: '4px' }}>
                        <span>Avg Severity: {inc.avg_severity}/5.0</span>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-primary)', fontStyle: 'italic', maxWidth: '200px' }}>
                        "{inc.description}"
                      </div>
                      {user?.role === 'Authority_Admin' && (
                        <button
                          type="button"
                          className="incident-popup-clear-btn"
                          onClick={(e) => handleResolveClusterFromMap(inc.cluster_id, e)}
                          title="Site is rectified: mark cleared and remove from map"
                        >
                          <CheckCircle size={12} /> Mark Cleared & Remove
                        </button>
                      )}
                    </div>
                  </Tooltip>
                </Marker>
              );
            })}

            {/* Live Device GPS Location Marker & Accuracy Ring */}
            {deviceCoords && (
              <>
                <Marker position={[deviceCoords.lat, deviceCoords.lng]} icon={createGPSLocationMarkerIcon()}>
                  <Tooltip permanent offset={[0, -10]}>
                    <span style={{ fontSize: '10.5px', fontWeight: '550', color: '#0284C7' }}>
                      📍 You Are Here (Live GPS &bull; &plusmn;{deviceCoords.accuracy}m)
                    </span>
                  </Tooltip>
                </Marker>
                <Circle
                  center={[deviceCoords.lat, deviceCoords.lng]}
                  radius={Math.max(150, deviceCoords.accuracy || 150)}
                  pathOptions={{ color: '#0EA5E9', fillColor: '#0EA5E9', fillOpacity: 0.12, weight: 1.5 }}
                />
              </>
            )}
            <MapClickInterceptor
              pinDropModeRef={pinDropModeRef}
              onPinDrop={(coords) => {
                setDroppedPinCoords(coords);
                setIsReportModalOpen(true);
                setPinDropMode(false);
              }}
              onSelectNode={setSelectedNode}
              proximityScope={proximityScope}
            />
          </MapContainer>
        </div>

        {/* 3-Column Dashboard Grid */}
        <div className="ios-dashboard-grid">
          {/* Column 1: Telemetry Controls */}
          <div className="ios-card ios-glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <h3 style={{ fontSize: '12px', fontWeight: '600', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', textTransform: 'uppercase' }}><Sliders size={14} color="var(--accent)" /> Telemetry Controls</h3>
              <IosSwitch checked={simMode} onChange={setSimMode} label="Simulation Mode" />
            </div>

            <div style={{ fontSize: '12px', background: 'var(--bg-primary)', padding: '10px 14px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Info size={13} color="var(--accent)" />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Location: <b style={{ color: 'var(--text-primary)' }}>{displayLabel}</b></span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)', display: 'block', textTransform: 'uppercase', fontWeight: '500' }}>Slope Angle</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>{activeEvalNode.slope}°</span>
              </div>
              <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)', display: 'block', textTransform: 'uppercase', fontWeight: '500' }}>Elevation</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>{activeEvalNode.elevation}m</span>
              </div>
            </div>

            {!simMode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-primary)', borderRadius: '12px', fontSize: '13px', border: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}><CloudRain size={13} /> Precipitation:</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{(Number(riskData.live_rainfall) || 0).toFixed(1)} mm/day</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-primary)', borderRadius: '12px', fontSize: '13px', border: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}><Thermometer size={13} /> Soil Saturation:</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{(Number(riskData.live_humidity) || 0).toFixed(0)}%</span>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="ios-slider-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '550' }}>
                    <span>Precipitation Input</span><span style={{ color: 'var(--accent)' }}>{rainfall} mm</span>
                  </div>
                  <input type="range" min="0" max="500" value={rainfall} onChange={(e) => setRainfall(e.target.value)} className="ios-slider" />
                </div>
                <div className="ios-slider-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '550' }}>
                    <span>Matrix Saturation</span><span style={{ color: 'var(--accent)' }}>{saturation}%</span>
                  </div>
                  <input type="range" min="10" max="100" value={saturation} onChange={(e) => setSaturation(e.target.value)} className="ios-slider" />
                </div>
              </div>
            )}

            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', fontWeight: '550' }}><Activity size={12} color="var(--accent)" /> Exposure Index Matrix</span>
              <div style={{ width: '100%', backgroundColor: 'var(--border-color)', borderRadius: '99px', height: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, (currentRainInt / 500) * 100)}%`, backgroundColor: gaugeColor, height: '100%', transition: 'width 0.4s ease-out' }}></div>
              </div>
            </div>
          </div>

          {/* Column 2: Risk Coefficient Gauge */}
          <div className="ios-card ios-glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', alignItems: 'center', textAlign: 'center' }}>
            <h3 style={{ fontSize: '12px', fontWeight: '600', margin: '0 0 12px 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', width: '100%' }}><Radio size={14} color="var(--accent)" /> Risk Coefficient</h3>
            <div style={{ position: 'relative', width: '150px', height: '150px', margin: '12px 0' }}>
              <svg width="150" height="150" viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
                <circle cx="50" cy="50" r="44" fill="transparent" stroke="var(--border-color)" strokeWidth="5.5" />
                <circle cx="50" cy="50" r="44" fill="transparent" stroke={gaugeColor} strokeWidth="6" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.4s ease-out' }} />
              </svg>
              <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                <span style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-1px' }}>{risk.toFixed(1)}<span style={{ fontSize: '16px', fontWeight: '500', color: 'var(--text-secondary)' }}>%</span></span>
                <span style={{ fontSize: '9px', fontWeight: '700', color: gaugeColor, textTransform: 'uppercase', marginTop: '2px' }}>
                  {isGuardActive ? 'Lowland Guard Active' : risk >= 85 ? 'Critical Threat' : risk >= 50 ? 'Active Warning' : 'Nominal Stability'}
                </span>
              </div>
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '600', textTransform: 'uppercase' }}>Dual-Stage ML Inference Core</div>
          </div>

          {/* Column 3: Communication Gateways & Broadcast Control */}
          <BroadcastControlCard
            riskData={riskData}
            riskPercentage={risk}
            isGuardActive={isGuardActive}
            gaugeColor={gaugeColor}
            user={user}
            triggerToast={triggerToast}
          />
        </div>
      </div>

      {/* Phase 3: Report Hazard Modal */}
      <ReportHazardModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        coordinates={droppedPinCoords}
        user={user}
        token={token}
        onReportSuccess={() => fetchActiveIncidents()}
        triggerToast={triggerToast}
      />

      {/* Phase 4: Authority Triage Dashboard */}
      <AuthorityDashboard
        isOpen={isAuthorityPortalOpen}
        onClose={() => setIsAuthorityPortalOpen(false)}
        user={user}
        token={token}
        onClusterUpdated={() => fetchActiveIncidents()}
        triggerToast={triggerToast}
      />

      {/* Phase 7: Relief Shelter Detail Modal */}
      <ShelterDetailModal
        isOpen={isShelterDetailOpen}
        onClose={() => setIsShelterDetailOpen(false)}
        shelter={selectedShelter}
        user={user}
        onPlanRoute={(targetShelter) => handlePlanEvacuationRoute(targetShelter)}
        onOpenOccupancyEdit={(targetShelter) => {
          setOccupancyEditShelter(targetShelter);
          setIsOccupancyModalOpen(true);
        }}
      />

      {/* Phase 7: Relief Shelter Occupancy Management Modal (Authority/Volunteer) */}
      <ShelterOccupancyModal
        isOpen={isOccupancyModalOpen}
        onClose={() => setIsOccupancyModalOpen(false)}
        shelter={occupancyEditShelter}
        token={token}
        triggerToast={triggerToast}
        onOccupancyUpdated={(updatedData) => {
          fetchShelters();
          if (selectedShelter && selectedShelter.id === updatedData.id) {
            setSelectedShelter(prev => ({ ...prev, ...updatedData }));
          }
        }}
      />

      {/* Phase 8: Offline Helplines Directory Modal */}
      <EmergencyHelplinesModal
        isOpen={isHelplinesModalOpen}
        onClose={() => setIsHelplinesModalOpen(false)}
      />

      {/* Missing Persons & Rescue Registry Modal */}
      <MissingPersonsModal
        isOpen={isMissingModalOpen}
        onClose={() => setIsMissingModalOpen(false)}
        user={user}
        token={token}
        shelters={shelters}
        triggerToast={triggerToast}
      />

      {/* System Settings, Cartography & GIS Layers Modal */}
      <SettingsLayersModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        showShelters={showShelters}
        setShowShelters={setShowShelters}
        showIncidents={showIncidents}
        setShowIncidents={setShowIncidents}
        showHotspots={showHotspots}
        setShowHotspots={setShowHotspots}
        showRadar={showRadar}
        setShowRadar={setShowRadar}
        showHillshade={showHillshade}
        setShowHillshade={setShowHillshade}
        showSlopeMesh={showSlopeMesh}
        setShowSlopeMesh={setShowSlopeMesh}
        baseLayer={baseLayer}
        setBaseLayer={setBaseLayer}
        theme={theme}
        setTheme={setTheme}
        onOpenHelplines={() => setIsHelplinesModalOpen(true)}
      />

      {/* System Location Permission Settings Pop-Up Dialog */}
      {showLocationPermissionPrompt && (
        <div className="auth-modal-backdrop" onClick={() => setShowLocationPermissionPrompt(false)} style={{ zIndex: 14000 }}>
          <div className="system-loc-popup-card ios-glass" onClick={(e) => e.stopPropagation()}>
            <div className="system-loc-popup-header">
              <div className="system-loc-icon-bubble">
                <MapPin size={22} color="#38BDF8" />
              </div>
              <div style={{ flex: 1 }}>
                <h3 className="system-loc-title">Enable Location in System Settings</h3>
                <span className="system-loc-subtitle">Device Geolocation Access Required</span>
              </div>
              <button className="auth-close-btn" onClick={() => setShowLocationPermissionPrompt(false)}>
                <X size={18} />
              </button>
            </div>

            <p className="system-loc-desc">
              TerraRisk AI requires device location permissions to pinpoint your live location on the disaster matrix and calculate safe evacuation routes.
            </p>

            <div className="system-loc-steps-box">
              <div className="system-loc-step-item">
                <span className="step-num">1</span>
                <div>
                  <strong>In your Browser:</strong> Click the <strong>Lock / Permissions 🔒 icon</strong> in your browser address bar and set <strong>Location</strong> to <strong>"Allow"</strong>.
                </div>
              </div>
              <div className="system-loc-step-item">
                <span className="step-num">2</span>
                <div>
                  <strong>In Windows Settings:</strong> Open <strong>Start &rarr; Settings &rarr; Privacy & Security &rarr; Location</strong> and toggle <strong>Location services</strong> ON.
                </div>
              </div>
            </div>

            <div className="system-loc-actions">
              <button
                type="button"
                className="btn-system-loc-dismiss"
                onClick={() => setShowLocationPermissionPrompt(false)}
              >
                Dismiss
              </button>
              <button
                type="button"
                className="btn-system-loc-retry"
                onClick={() => {
                  setShowLocationPermissionPrompt(false);
                  requestDeviceLocation(true);
                }}
              >
                <RefreshCw size={14} className={isLocatingDevice ? 'spin-anim' : ''} />
                <span>Try Again</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
        triggerToast={triggerToast}
      />

      {/* Mobile Bottom Navigation Quick Actions */}
      <MobileBottomNav
        onCheckSafety={handleCheckMyArea}
        onReportHazard={handleStartReportHazard}
        onSafeRoute={() => handlePlanEvacuationRoute()}
        onOpenHelplines={() => setIsHelplinesModalOpen(true)}
        onOpenMenu={() => setIsSidebarOpen(true)}
        planningRoute={planningRoute}
        checkingSafety={checkingSafety}
        deviceCoords={deviceCoords}
      />

      {/* Toast Notification */}
      <div className={`ios-toast ios-glass ${toast.show ? 'show' : ''}`} style={{ borderLeft: `4px solid ${toast.type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)'}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {toast.type === 'success' ? <CheckCircle size={18} color="var(--accent-green)" /> : <AlertTriangle size={18} color="var(--accent-red)" />}
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>{toast.message}</span>
        </div>
      </div>
    </div>
  );
}