import { useState } from 'react';
import { X, Sliders, Layers, PhoneCall, Radio, Eye, Sun, Moon, Map, CloudRain, Mountain, Activity, Check } from 'lucide-react';
import { BASE_LAYERS } from '../constants/mapLayers';

export default function SettingsLayersModal({
  isOpen,
  onClose,
  showShelters,
  setShowShelters,
  showIncidents,
  setShowIncidents,
  showHotspots,
  setShowHotspots,
  showRadar,
  setShowRadar,
  showHillshade,
  setShowHillshade,
  showSlopeMesh,
  setShowSlopeMesh,
  baseLayer,
  setBaseLayer,
  theme,
  setTheme,
  onOpenHelplines
}) {
  if (!isOpen) return null;

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 12000 }}>
      <div className="settings-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="auth-header-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38BDF8' }}>
              <Sliders size={22} />
            </div>
            <div>
              <h2 className="auth-title">System Settings & GIS Layers</h2>
              <span className="auth-subtitle">Cartographic Overlays & Emergency Controls</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="settings-modal-body">
          {/* Section 1: Base Map Style */}
          <div className="form-section-label" style={{ marginTop: 0 }}>Base Map Cartography</div>
          <div className="basemap-selector-grid">
            {Object.keys(BASE_LAYERS).map(key => {
              const layer = BASE_LAYERS[key];
              const isSelected = baseLayer === key;
              return (
                <button
                  key={key}
                  className={`basemap-option-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setBaseLayer(key)}
                >
                  <Map size={16} color={isSelected ? '#38BDF8' : 'var(--text-secondary)'} />
                  <span>{layer.name}</span>
                  {isSelected && <Check size={14} color="#38BDF8" style={{ marginLeft: 'auto' }} />}
                </button>
              );
            })}
          </div>

          {/* Section 2: GIS & Disaster Overlays */}
          <div className="form-section-label" style={{ marginTop: '16px' }}>Active GIS Overlays</div>
          <div className="settings-toggles-grid">
            <div className="setting-toggle-row">
              <div className="setting-toggle-info">
                <span className="setting-toggle-title">⛺ Relief Shelters & Camps</span>
                <span className="setting-toggle-sub">Display KSDMA designated relief camps & supplies</span>
              </div>
              <label className="ios-switch-inline">
                <input
                  type="checkbox"
                  checked={showShelters}
                  onChange={(e) => setShowShelters(e.target.checked)}
                />
                <span className="ios-slider-pill" />
              </label>
            </div>

            <div className="setting-toggle-row">
              <div className="setting-toggle-info">
                <span className="setting-toggle-title">⚠️ Incident Hazard Clusters</span>
                <span className="setting-toggle-sub">Citizen-reported & AI-verified disaster clusters</span>
              </div>
              <label className="ios-switch-inline">
                <input
                  type="checkbox"
                  checked={showIncidents}
                  onChange={(e) => setShowIncidents(e.target.checked)}
                />
                <span className="ios-slider-pill" />
              </label>
            </div>

            <div className="setting-toggle-row">
              <div className="setting-toggle-info">
                <span className="setting-toggle-title">📍 Historic Landslide Epicenters</span>
                <span className="setting-toggle-sub">Wayanad (Chooralmala, Mundakkai, Puthumala) hotspots</span>
              </div>
              <label className="ios-switch-inline">
                <input
                  type="checkbox"
                  checked={showHotspots}
                  onChange={(e) => setShowHotspots(e.target.checked)}
                />
                <span className="ios-slider-pill" />
              </label>
            </div>

            <div className="setting-toggle-row">
              <div className="setting-toggle-info">
                <span className="setting-toggle-title">🌧️ Live Doppler Radar (RainViewer)</span>
                <span className="setting-toggle-sub">Real-time precipitation radar reflectivity scan</span>
              </div>
              <label className="ios-switch-inline">
                <input
                  type="checkbox"
                  checked={showRadar}
                  onChange={(e) => setShowRadar(e.target.checked)}
                />
                <span className="ios-slider-pill" />
              </label>
            </div>

            <div className="setting-toggle-row">
              <div className="setting-toggle-info">
                <span className="setting-toggle-title">⛰️ NASA SRTM Terrain Hillshade</span>
                <span className="setting-toggle-sub">3D Elevation relief shaded topography</span>
              </div>
              <label className="ios-switch-inline">
                <input
                  type="checkbox"
                  checked={showHillshade}
                  onChange={(e) => setShowHillshade(e.target.checked)}
                />
                <span className="ios-slider-pill" />
              </label>
            </div>

            <div className="setting-toggle-row">
              <div className="setting-toggle-info">
                <span className="setting-toggle-title">📐 Western Ghats Slope Vulnerability</span>
                <span className="setting-toggle-sub">Color-coded slope angle overlay (&lt;15°, 15-30°, &gt;30°)</span>
              </div>
              <label className="ios-switch-inline">
                <input
                  type="checkbox"
                  checked={showSlopeMesh}
                  onChange={(e) => setShowSlopeMesh(e.target.checked)}
                />
                <span className="ios-slider-pill" />
              </label>
            </div>
          </div>

          {/* Section 3: Quick Utilities */}
          <div className="form-section-label" style={{ marginTop: '16px' }}>Emergency Directory & Display</div>
          <div className="settings-actions-grid">
            <button
              className="btn-settings-action"
              onClick={() => { onClose(); if (onOpenHelplines) onOpenHelplines(); }}
            >
              <PhoneCall size={16} color="#30D158" />
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontWeight: '700', fontSize: '12.5px', color: 'var(--text-primary)' }}>24/7 Helplines Directory</div>
                <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>KSDMA (1077, 1070), NDRF, Police, Ambulance</div>
              </div>
            </button>

            <button
              className="btn-settings-action"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              {theme === 'light' ? <Moon size={16} color="#38BDF8" /> : <Sun size={16} color="#F59E0B" />}
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontWeight: '700', fontSize: '12.5px', color: 'var(--text-primary)' }}>
                  Theme: {theme === 'light' ? 'Light Mode' : 'Dark Glassmorphic'}
                </div>
                <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>Switch visual aesthetic mode</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
