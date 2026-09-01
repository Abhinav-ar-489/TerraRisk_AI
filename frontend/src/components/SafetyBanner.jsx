import { ShieldCheck, AlertTriangle, AlertOctagon, CloudRain, Thermometer, Mountain, Building2, PhoneCall, X, Navigation, Radio } from 'lucide-react';

export default function SafetyBanner({ safetyData, onClose, onFocusHome }) {
  if (!safetyData) return null;

  const {
    status = 'Safe',
    risk_percentage = 0,
    live_rainfall = 0,
    live_humidity = 0,
    elevation = 0,
    slope = 0,
    location_name = 'Your Location',
    advisory = '',
    nearest_shelter = null,
    checked_at = ''
  } = safetyData;

  const isCritical = status === 'Critical';
  const isAdvisory = status === 'Advisory';

  const statusThemeClass = isCritical
    ? 'safety-banner-critical'
    : isAdvisory
    ? 'safety-banner-advisory'
    : 'safety-banner-safe';

  const StatusIcon = isCritical ? AlertOctagon : isAdvisory ? AlertTriangle : ShieldCheck;

  return (
    <div className={`safety-banner-container ios-card ios-glass ${statusThemeClass}`}>
      <div className="safety-banner-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="safety-status-icon-frame">
            <StatusIcon size={22} className="safety-animated-icon" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="safety-status-badge">{status} Level Alert</span>
              <span className="safety-timestamp">Checked: {checked_at ? new Date(checked_at).toLocaleTimeString() : 'Live'}</span>
            </div>
            <h3 className="safety-location-title">{location_name}</h3>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onFocusHome && (
            <button onClick={onFocusHome} className="safety-action-btn" title="Focus map on my coordinates">
              <Navigation size={13} /> Focus Map
            </button>
          )}
          <button onClick={onClose} className="safety-close-btn" title="Close safety banner">
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Advisory message */}
      <div className="safety-advisory-box">
        <Radio size={14} className="safety-advisory-icon" />
        <p className="safety-advisory-text">{advisory}</p>
      </div>

      {/* Metrics Row */}
      <div className="safety-metrics-grid">
        <div className="safety-metric-pill">
          <span className="safety-metric-label">Landslide Risk</span>
          <span className="safety-metric-value" style={{ color: isCritical ? 'var(--accent-red)' : isAdvisory ? 'var(--accent-orange)' : 'var(--accent-green)' }}>
            {risk_percentage.toFixed(1)}%
          </span>
        </div>

        <div className="safety-metric-pill">
          <span className="safety-metric-label"><CloudRain size={12} /> Live Rainfall</span>
          <span className="safety-metric-value">{live_rainfall.toFixed(1)} mm</span>
        </div>

        <div className="safety-metric-pill">
          <span className="safety-metric-label"><Thermometer size={12} /> Saturation</span>
          <span className="safety-metric-value">{live_humidity.toFixed(0)}%</span>
        </div>

        <div className="safety-metric-pill">
          <span className="safety-metric-label"><Mountain size={12} /> Terrain</span>
          <span className="safety-metric-value">{slope}° / {elevation.toFixed(0)}m</span>
        </div>
      </div>

      {/* Nearest Relief Shelter & Incident Summary */}
      <div className="safety-shelter-incident-row">
        {nearest_shelter ? (
          <div className="safety-shelter-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <Building2 size={14} color="var(--accent)" />
              <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                Nearest Relief Shelter ({nearest_shelter.distance_km} km away)
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>{nearest_shelter.name}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  District: {nearest_shelter.district} | Available Beds: <b style={{ color: 'var(--accent-green)' }}>{nearest_shelter.available_capacity}</b> / {nearest_shelter.capacity}
                </div>
              </div>
              {nearest_shelter.contact_number && (
                <a href={`tel:${nearest_shelter.contact_number}`} className="safety-phone-link">
                  <PhoneCall size={12} /> Call
                </a>
              )}
            </div>
          </div>
        ) : (
          <div className="safety-shelter-card" style={{ fontStyle: 'italic', color: 'var(--text-secondary)', fontSize: '12px' }}>
            No registered shelters within 30 km sector.
          </div>
        )}
      </div>
    </div>
  );
}
