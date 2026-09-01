import { useState } from 'react';
import { ChevronDown, ChevronUp, Mountain } from 'lucide-react';

export default function TerrainSlopeLegend() {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <div className="terrain-slope-legend-container ios-glass">
      <div className="legend-header" onClick={() => setCollapsed(!collapsed)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Mountain size={13} color="var(--accent)" />
          <span className="legend-title">GIS Topography Legend</span>
        </div>
        <button className="legend-toggle-btn">
          {collapsed ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
      </div>

      {!collapsed && (
        <div className="legend-body">
          {/* Slope Angles */}
          <div className="legend-section">
            <span className="legend-subheading">Slope Vulnerability</span>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ background: '#30D158' }} />
              <span className="legend-text">&lt; 15&deg; Safe Lowland Coastal</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ background: '#F59E0B' }} />
              <span className="legend-text">15&deg; &ndash; 30&deg; Moderate Incline</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-dot" style={{ background: '#EF4444' }} />
              <span className="legend-text">&gt; 30&deg; Critical Slope Escarpment</span>
            </div>
          </div>

          {/* RainViewer Doppler Radar Scale */}
          <div className="legend-section">
            <span className="legend-subheading">Doppler Radar Rate</span>
            <div className="legend-radar-gradient-bar" />
            <div className="legend-radar-labels">
              <span>Light (5mm)</span>
              <span>Mod (25mm)</span>
              <span>Torrent (&gt;80mm)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
