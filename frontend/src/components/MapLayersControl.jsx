import { useState } from 'react';
import { Layers, Sliders, Mountain, CloudRain, Check, ChevronDown, ChevronUp, Flame, ShieldAlert } from 'lucide-react';
import { BASE_LAYERS } from '../constants/mapLayers';

export default function MapLayersControl({
  baseLayer,
  onBaseLayerChange,
  showRadar,
  onToggleRadar,
  radarOpacity,
  onRadarOpacityChange,
  showHillshade,
  onToggleHillshade,
  showSlopeMesh,
  onToggleSlopeMesh,
  showHeatmap,
  onToggleHeatmap,
  showIncidents,
  onToggleIncidents,
  showHotspots,
  onToggleHotspots,
  showShelters,
  onToggleShelters,
  showTelemetryNodes,
  onToggleTelemetryNodes
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="gis-layers-control-container">
      {/* Floating Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`gis-layers-trigger-btn ios-glass ${isOpen ? 'active' : ''}`}
        title="Toggle GIS Visual Map Layers"
      >
        <Layers size={16} color="var(--accent)" />
        <span>Map Layers</span>
        {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Layer Control Menu Card */}
      {isOpen && (
        <div className="gis-layers-dropdown ios-glass">
          <div className="gis-layers-header">
            <span style={{ fontSize: '11.5px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sliders size={13} color="var(--accent)" /> GIS Visual Overlays
            </span>
          </div>

          {/* Base Layer Switcher */}
          <div className="gis-layer-section">
            <span className="gis-section-label">Base Terrain Tile</span>
            <div className="gis-base-layer-grid">
              {Object.values(BASE_LAYERS).map(l => (
                <div
                  key={l.id}
                  onClick={() => onBaseLayerChange(l.id)}
                  className={`gis-base-tile-card ${baseLayer === l.id ? 'selected' : ''}`}
                >
                  <span className="gis-tile-name">{l.name.split(' ')[0]}</span>
                  {baseLayer === l.id && <Check size={12} color="var(--accent)" />}
                </div>
              ))}
            </div>
          </div>

          {/* Dynamic Radar Layer Controls */}
          <div className="gis-layer-section">
            <div className="gis-toggle-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CloudRain size={15} color="#38BDF8" />
                <span className="gis-toggle-title">Live Doppler Radar</span>
              </div>
              <input
                type="checkbox"
                checked={showRadar}
                onChange={(e) => onToggleRadar(e.target.checked)}
                className="gis-checkbox"
              />
            </div>

            {showRadar && (
              <div className="gis-radar-opacity-control">
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                  <span>Radar Opacity</span>
                  <span style={{ fontWeight: '800', color: 'var(--text-primary)' }}>{Math.round(radarOpacity * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={radarOpacity}
                  onChange={(e) => onRadarOpacityChange(parseFloat(e.target.value))}
                  className="ios-slider gis-mini-slider"
                />
              </div>
            )}
          </div>

          {/* 3D Hillshade Relief Layer */}
          <div className="gis-layer-section">
            <div className="gis-toggle-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Mountain size={15} color="#F59E0B" />
                <div>
                  <span className="gis-toggle-title">3D Hillshade Relief</span>
                  <span className="gis-toggle-desc">ESRI Topographic Relief Contour</span>
                </div>
              </div>
              <input
                type="checkbox"
                checked={showHillshade}
                onChange={(e) => onToggleHillshade(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
          </div>

          {/* High-Risk Steep Slopes (>30°) Mesh */}
          <div className="gis-layer-section">
            <div className="gis-toggle-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Flame size={15} color="#EF4444" />
                <div>
                  <span className="gis-toggle-title">Steep Slopes (&gt;30°)</span>
                  <span className="gis-toggle-desc">High ML Susceptibility Escarpments</span>
                </div>
              </div>
              <input
                type="checkbox"
                checked={showSlopeMesh}
                onChange={(e) => onToggleSlopeMesh(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
          </div>

          {/* Dynamic Automated Risk Heatmap (Kernel Density) */}
          <div className="gis-layer-section">
            <div className="gis-toggle-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '15px' }}>🔥</span>
                <div>
                  <span className="gis-toggle-title">Dynamic Risk Heatmap</span>
                  <span className="gis-toggle-desc">Live Rainfall & Slope Susceptibility</span>
                </div>
              </div>
              <input
                type="checkbox"
                checked={showHeatmap}
                onChange={(e) => onToggleHeatmap(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
          </div>

          {/* Standard Map Markers & Overlays */}
          <div className="gis-layer-section" style={{ borderBottom: 'none', paddingBottom: '2px' }}>
            <div className="gis-toggle-row" style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldAlert size={15} color="var(--accent)" />
                <span className="gis-toggle-title">Incident Clusters</span>
              </div>
              <input
                type="checkbox"
                checked={showIncidents}
                onChange={(e) => onToggleIncidents(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
            <div className="gis-toggle-row" style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px' }}>🏠</span>
                <span className="gis-toggle-title">Relief Shelters</span>
              </div>
              <input
                type="checkbox"
                checked={showShelters}
                onChange={(e) => onToggleShelters(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
            <div className="gis-toggle-row" style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px' }}>📍</span>
                <span className="gis-toggle-title">Historic Hotspots</span>
              </div>
              <input
                type="checkbox"
                checked={showHotspots}
                onChange={(e) => onToggleHotspots(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
            <div className="gis-toggle-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px' }}>📡</span>
                <span className="gis-toggle-title">Sector Monitoring Grid</span>
              </div>
              <input
                type="checkbox"
                checked={showTelemetryNodes}
                onChange={(e) => onToggleTelemetryNodes(e.target.checked)}
                className="gis-checkbox"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
