import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip, Circle, useMapEvents } from 'react-leaflet';
import { Shield, Radio, Sliders, Activity, Info, MapPin, Send, Sun, Moon, CheckCircle, AlertTriangle, CloudRain, Thermometer, Cloud, CloudLightning } from 'lucide-react';
import axios from 'axios';
import L from 'leaflet';
import './App.css';

const KERALA_BOUNDS = [[8.1, 74.3], [12.9, 77.6]];

const KERALA_NODES = [
  { id: 'Wayanad Ridge (Node A)', lat: 11.6920, lng: 76.1450, slope: 38.5, elevation: 950, soil: 1 },
  { id: 'Meppadi Sector (Node B)', lat: 11.5542, lng: 76.1308, slope: 42.0, elevation: 1120, soil: 1 },
  { id: 'Idukki Valley (Node C)', lat: 9.8492, lng: 76.9792, slope: 18.2, elevation: 650, soil: 2 },
  { id: 'Munnar Slope (Node D)', lat: 10.0889, lng: 77.0595, slope: 31.4, elevation: 1450, soil: 3 }
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

function IosSwitch({ checked, onChange, label }) {
  return (
    <div className="ios-switch-wrapper" onClick={() => onChange(!checked)}>
      <div className={`ios-switch-bg ${checked ? 'active' : ''}`}>
        <div className="ios-switch-thumb" />
      </div>
      {label && <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>{label}</span>}
    </div>
  );
}

export default function App() {
  const [selectedNode, setSelectedNode] = useState(KERALA_NODES[0]);
  const [simMode, setSimMode] = useState(false);
  const [showHotspots, setShowHotspots] = useState(true);
  const [hotspots, setHotspots] = useState([]);
  const [rainfall, setRainfall] = useState(150);
  const [saturation, setSaturation] = useState(60);
  const [riskData, setRiskData] = useState({ risk_percentage: 0, live_rainfall: 0, live_humidity: 50, alert_text: "", geo_name: "", true_elevation: 0 });
  const [forecastData, setForecastData] = useState([]);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [toast, setToast] = useState({ show: false, message: '', type: 'info' });
  const [recipientMobile, setRecipientMobile] = useState("+916282115954");

  const simModeRef = useRef(simMode);
  const rainfallRef = useRef(rainfall);
  const saturationRef = useRef(saturation);

  useEffect(() => { simModeRef.current = simMode; }, [simMode]);
  useEffect(() => { rainfallRef.current = rainfall; }, [rainfall]);
  useEffect(() => { saturationRef.current = saturation; }, [saturation]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/hotspots')
      .then(res => setHotspots(res.data))
      .catch(err => console.log("System data arrays synced."));
  }, []);

  const transmitTelemetry = (nodeObj, currentSimMode, currentRain, currentSat) => {
    axios.post('http://127.0.0.1:5000/api/predict', {
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
          setSelectedNode(prev => ({ ...prev, elevation: res.data.true_elevation }));
        }
        if (res.data.geo_name && nodeObj.id.startsWith("Sector Grid Box")) {
          setSelectedNode(prev => ({ ...prev, displayName: res.data.geo_name }));
        }
      })
      .catch(err => console.log("Matrix execution error."));

    axios.post('http://127.0.0.1:5000/api/forecast', { lat: nodeObj.lat, lng: nodeObj.lng })
      .then(res => {
        if (res.data.success) setForecastData(res.data.forecast);
      })
      .catch(err => console.log("Forecast sync gap."));
  };

  useEffect(() => {
    transmitTelemetry(selectedNode, simMode, rainfall, saturation);
  }, [selectedNode, simMode, rainfall, saturation]);

  const triggerToast = (message, type = 'info') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast(prev => ({ ...prev, show: false })), 4000);
  };

  const handleSmsBlast = async () => {
    try {
      triggerToast("Accessing telecom gateway...", "info");
      const res = await axios.post('http://127.0.0.1:5000/api/broadcast', {
        alert_text: riskData.alert_text,
        recipient_mobile: recipientMobile
      });
      if (res.data.success) {
        triggerToast("✓ SMS Broadcast Dispatched via Twilio", "success");
      } else {
        triggerToast(`Dispatch exception logged inside engine console`, "error");
      }
    } catch (err) {
      triggerToast("Connection handshake error.", "error");
    }
  };

  function MapClickInterceptor() {
    useMapEvents({
      click(e) {
        const { lat, lng } = e.latlng;
        const ghatsInversionFactor = (12.9 - lat) / (12.9 - 8.1);
        const highlandBoundaryLng = 75.85 + (ghatsInversionFactor * 0.65);
        const midlandBoundaryLng = highlandBoundaryLng - 0.35;

        let calculatedSlope = 1.5;
        let soilType = 2;

        if (lng >= highlandBoundaryLng) {
          const depthIntoMountains = (lng - highlandBoundaryLng) / (77.6 - highlandBoundaryLng);
          calculatedSlope = Math.min(45.0, 18.0 + (depthIntoMountains * 35));
          soilType = 1;
        } else if (lng >= midlandBoundaryLng && lng < highlandBoundaryLng) {
          const depthIntoMidlands = (lng - midlandBoundaryLng) / (highlandBoundaryLng - midlandBoundaryLng);
          calculatedSlope = 2.0 + (depthIntoMidlands * 10.0);
          soilType = 2;
        } else {
          const depthIntoLowlands = Math.max(0, (lng - 75.1) / (midlandBoundaryLng - 75.1));
          calculatedSlope = 0.5 + (depthIntoLowlands * 1.5);
          soilType = 3;
        }

        const freshNode = {
          id: `Sector Grid Box (${lat.toFixed(3)}°N, ${lng.toFixed(3)}°E)`,
          displayName: "Resolving Topography...",
          lat: lat,
          lng: lng,
          slope: parseFloat(calculatedSlope.toFixed(1)),
          elevation: 0,
          soil: soilType
        };

        setSelectedNode(freshNode);
      },
    });
    return null;
  }

  const dominantWeather = forecastData[0]?.condition || "clear";
  let weatherThemeClass = "weather-theme-clear";
  if (dominantWeather === "rain") weatherThemeClass = "weather-theme-rain";
  else if (dominantWeather === "thunderstorm") weatherThemeClass = "weather-theme-thunder";
  else if (dominantWeather === "clouds") weatherThemeClass = "weather-theme-clouds";

  const renderWeatherIcon = (cond) => {
    switch (cond) {
      case 'rain': return <CloudRain size={24} className="weather-animated-icon color-rain" />;
      case 'thunderstorm': return <CloudLightning size={24} className="weather-animated-icon color-thunder" />;
      case 'clouds': return <Cloud size={24} className="weather-animated-icon color-cloud" />;
      default: return <Sun size={24} className="weather-animated-icon color-sun" />;
    }
  };

  const risk = riskData.risk_percentage || 0;
  const isGuardActive = selectedNode.slope < 8.0 && selectedNode.elevation < 150.0;
  const gaugeColor = isGuardActive ? 'var(--accent-green)' : risk >= 85 ? 'var(--accent-red)' : risk >= 50 ? 'var(--accent-orange)' : 'var(--accent-green)';
  const circumference = 2 * Math.PI * 44;
  const strokeDashoffset = circumference - (risk / 100) * circumference;
  const displayLabel = selectedNode.displayName || selectedNode.id;
  const currentRainInt = simMode ? rainfall : (riskData.live_rainfall || 0);

  // Apply the weather theme to the global background if the system is in light mode
  const globalAppLayoutClass = theme === 'light' ? `global-bg-${dominantWeather}` : '';

  return (
    <div className={`app-main-viewport-frame ${globalAppLayoutClass}`} style={{ minHeight: '100vh', paddingBottom: '40px', position: 'relative', overflowX: 'hidden' }}>
      <div style={{ position: 'fixed', top: '10%', left: '5%', width: '350px', height: '350px', borderRadius: '50%', background: theme === 'dark' ? 'radial-gradient(circle, rgba(10, 132, 255, 0.08) 0%, rgba(10, 132, 255, 0) 70%)' : 'radial-gradient(circle, rgba(10, 132, 255, 0.03) 0%, rgba(10, 132, 255, 0) 70%)', filter: 'blur(80px)', zIndex: -1, pointerEvents: 'none' }} />

      <header className="ios-glass" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 32px', borderRadius: '24px', boxShadow: 'var(--shadow)', marginBottom: '24px', position: 'sticky', top: '16px', zIndex: 1000, maxWidth: '1240px', margin: '16px auto', width: 'calc(100% - 32px)' }}>
        <div>
          <h1 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '20px', fontWeight: '800', letterSpacing: '0.5px' }}>TERRARISK <span style={{ color: 'var(--accent)' }}>CORE</span></h1>
          <p style={{ margin: '2px 0 0 0', color: 'var(--text-secondary)', fontSize: '10px', fontWeight: '700', textTransform: 'uppercase' }}>Analytical Matrix Stream</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <IosSwitch checked={showHotspots} onChange={setShowHotspots} label="Overlay Records" />
          <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} style={{ background: 'var(--border-color)', border: 'none', borderRadius: '50%', width: '36px', height: '36px', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>

      <div className="app-container">
        <div className="ios-card" style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', height: '390px', width: '100%', zIndex: 10, marginBottom: '20px' }}>
          <MapContainer center={[11.25, 75.8]} zoom={9} minZoom={7.5} maxBounds={KERALA_BOUNDS} maxBoundsViscosity={1.0} style={{ height: '100%', width: '100%' }}>
            <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" attribution="Tiles &copy; Esri" />
            <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png" zIndex={10} />

            {KERALA_NODES.map((node, i) => (
              <Marker key={i} position={[node.lat, node.lng]} icon={createMarkerIcon(selectedNode.id === node.id)} eventHandlers={{ click: () => setSelectedNode(node) }}>
                <Tooltip direction="top" offset={[0, -5]}>
                  <div style={{ color: 'var(--text-primary)', fontSize: '11px', fontWeight: '600' }}>{node.id.split(' (')[0]}</div>
                </Tooltip>
              </Marker>
            ))}

            {showHotspots && hotspots.map((spot, i) => (
              <React.Fragment key={i}>
                <Marker position={[spot.lat, spot.lng]} icon={createHotspotIcon()}>
                  <Tooltip direction="top"><span style={{ color: 'var(--text-primary)', fontWeight: '600', fontSize: '11px' }}>Historic: {spot.name}</span></Tooltip>
                </Marker>
                <Circle center={[spot.lat, spot.lng]} radius={10000} pathOptions={{ color: 'var(--accent-red)', fillColor: 'var(--accent-red)', fillOpacity: 0.03, weight: 1 }} />
              </React.Fragment>
            ))}

            {!KERALA_NODES.some(n => n.id === selectedNode.id) && (
              <Marker position={[selectedNode.lat, selectedNode.lng]} icon={createMarkerIcon(true)}>
                <Tooltip permanent offset={[0, -5]}>
                  <div style={{ color: 'var(--accent)', fontSize: '11px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}><MapPin size={10} /> Target Node Locked</div>
                </Tooltip>
              </Marker>
            )}
            <MapClickInterceptor />
          </MapContainer>
        </div>

        {/* Weather UI Segment Wrapper */}
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
                  <span className="forecast-humidity-text">💧 {f.humidity}% saturation</span>
                </div>
              ))
            ) : (
              <div className="weather-loading-fallback">Awaiting network coordinate validation loop...</div>
            )}
          </div>
        </div>

        <div className="ios-dashboard-grid">
          <div className="ios-card ios-glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <h3 style={{ fontSize: '12px', fontWeight: '700', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', textTransform: 'uppercase' }}><Sliders size={14} color="var(--accent)" /> Telemetry Controls</h3>
              <IosSwitch checked={simMode} onChange={setSimMode} label="Simulation Mode" />
            </div>

            <div style={{ fontSize: '12px', background: 'var(--bg-primary)', padding: '10px 14px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Info size={13} color="var(--accent)" />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Location: <b style={{ color: 'var(--text-primary)' }}>{displayLabel}</b></span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)', display: 'block', textTransform: 'uppercase', fontWeight: '700' }}>Slope Angle</span>
                <span style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)' }}>{selectedNode.slope}°</span>
              </div>
              <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)', display: 'block', textTransform: 'uppercase', fontWeight: '700' }}>Elevation</span>
                <span style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)' }}>{selectedNode.elevation}m</span>
              </div>
            </div>

            {!simMode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-primary)', borderRadius: '12px', fontSize: '13px', border: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}><CloudRain size={13} /> Precipitation:</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>{riskData.live_rainfall.toFixed(1)} mm/day</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-primary)', borderRadius: '12px', fontSize: '13px', border: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}><Thermometer size={13} /> Soil Saturation:</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: '700' }}>{riskData.live_humidity.toFixed(0)}%</span>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="ios-slider-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '700' }}>
                    <span>Precipitation Input</span><span style={{ color: 'var(--accent)' }}>{rainfall} mm</span>
                  </div>
                  <input type="range" min="0" max="500" value={rainfall} onChange={(e) => setRainfall(e.target.value)} className="ios-slider" />
                </div>
                <div className="ios-slider-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '700' }}>
                    <span>Matrix Saturation</span><span style={{ color: 'var(--accent)' }}>{saturation}%</span>
                  </div>
                  <input type="range" min="10" max="100" value={saturation} onChange={(e) => setSaturation(e.target.value)} className="ios-slider" />
                </div>
              </div>
            )}

            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', fontWeight: '700' }}><Activity size={12} color="var(--accent)" /> Exposure Index Matrix</span>
              <div style={{ width: '100%', backgroundColor: 'var(--border-color)', borderRadius: '99px', height: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, (currentRainInt / 500) * 100)}%`, backgroundColor: gaugeColor, height: '100%', transition: 'width 0.4s ease-out' }}></div>
              </div>
            </div>
          </div>

          <div className="ios-card ios-glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', alignItems: 'center', textAlign: 'center' }}>
            <h3 style={{ fontSize: '12px', fontWeight: '700', margin: '0 0 12px 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', width: '100%' }}><Radio size={14} color="var(--accent)" /> Risk Coefficient</h3>
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
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '600', textTransform: 'uppercase' }}>XGBoost Inference Node</div>
          </div>

          <div className="ios-card ios-glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '12px', fontWeight: '700', margin: '0 0 4px 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}><Shield size={14} color="var(--accent)" /> Broadcast Control</h3>
            {risk >= 80 && !isGuardActive ? (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between', gap: '12px' }}>
                <div style={{ background: 'var(--bg-primary)', padding: '12px 14px', borderLeft: `4px solid ${gaugeColor}`, borderRadius: '12px', fontSize: '12.5px', color: 'var(--text-primary)', maxHeight: '75px', overflowY: 'auto', border: '1px solid var(--border-color)' }}>{riskData.alert_text}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <input type="text" value={recipientMobile} onChange={(e) => setRecipientMobile(e.target.value)} style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', padding: '10px 12px', borderRadius: '10px', fontSize: '13px', width: '100%' }} />
                </div>
                <button onClick={handleSmsBlast} className="ios-button ios-button-danger" style={{ width: '100%' }}><Send size={14} color="#FFF" /> Transmit Broadcast</button>
              </div>
            ) : (
              <div style={{ color: 'var(--accent-green)', fontSize: '12px', padding: '16px', background: 'var(--bg-primary)', borderRadius: '12px', border: '1px dashed var(--accent-green)', fontWeight: '600', textAlign: 'center', margin: 'auto 0' }}>Nominal parameters verified across active field arrays. Broadcast transmission gateways locked.</div>
            )}
          </div>
        </div>
      </div>

      <div className={`ios-toast ios-glass ${toast.show ? 'show' : ''}`} style={{ borderLeft: `4px solid ${toast.type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)'}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {toast.type === 'success' ? <CheckCircle size={18} color="var(--accent-green)" /> : <AlertTriangle size={18} color="var(--accent-red)" />}
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>{toast.message}</span>
        </div>
      </div>
    </div>
  );
}
