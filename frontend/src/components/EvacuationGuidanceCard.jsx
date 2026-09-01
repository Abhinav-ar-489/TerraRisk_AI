import { useState } from 'react';
import { Navigation, Phone, ShieldCheck, AlertTriangle, ChevronDown, ChevronUp, X, MapPin, Clock } from 'lucide-react';

export default function EvacuationGuidanceCard({ routePlan, onClose, onFocusShelter }) {
  const [expanded, setExpanded] = useState(false);

  if (!routePlan || !routePlan.success) return null;

  const dest = routePlan.destination_shelter;
  const isDirect = routePlan.avoided_hazards_count === 0;

  return (
    <div className="evacuation-guidance-card ios-glass">
      {/* Top Banner */}
      <div className="evac-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="evac-icon-badge">
            <Navigation size={16} color="#FFF" />
          </div>
          <div>
            <div className="evac-card-title-row">
              <span className="evac-card-title">SAFE EVACUATION ROUTE</span>
              <span className={`evac-safety-badge ${isDirect ? 'direct' : 'detour'}`}>
                {isDirect ? <ShieldCheck size={11} /> : <AlertTriangle size={11} />}
                {routePlan.safety_status}
              </span>
            </div>
            <span className="evac-card-dest-name">
              📍 Dest: <strong style={{ color: 'var(--text-primary)' }}>{dest?.name}</strong> ({dest?.district})
            </span>
          </div>
        </div>

        <button onClick={onClose} className="evac-close-btn" title="Clear Route">
          <X size={15} />
        </button>
      </div>

      {/* Metrics Strip */}
      <div className="evac-metrics-strip">
        <div className="evac-metric-box">
          <span className="evac-metric-label"><Navigation size={10} /> Total Distance</span>
          <span className="evac-metric-val">{routePlan.total_distance_km} km</span>
        </div>
        <div className="evac-metric-box">
          <span className="evac-metric-label"><Clock size={10} /> Estimated ETA</span>
          <span className="evac-metric-val">{routePlan.estimated_time_mins} mins</span>
        </div>
        <div className="evac-metric-box">
          <span className="evac-metric-label">Camp Capacity</span>
          <span className="evac-metric-val" style={{ color: 'var(--accent-green)' }}>
            {dest?.available_spots ?? (dest?.capacity - dest?.occupied)} spots left
          </span>
        </div>
      </div>

      {/* Turn-by-Turn Expandable Steps */}
      <div className="evac-steps-container">
        <button
          onClick={() => setExpanded(!expanded)}
          className="evac-steps-toggle-btn"
        >
          <span>Turn-by-Turn Safety Directions ({routePlan.turn_by_turn?.length || 0} steps)</span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {expanded && routePlan.turn_by_turn && (
          <div className="evac-steps-list">
            {routePlan.turn_by_turn.map((step, idx) => (
              <div key={idx} className="evac-step-item">
                <div className="evac-step-num">{idx + 1}</div>
                <div className="evac-step-info">
                  <span className="evac-step-instruction">{step.instruction}</span>
                  {step.distance_km > 0 && (
                    <span className="evac-step-dist">{step.distance_km} km</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="evac-card-actions">
        {dest?.contact_number && (
          <a
            href={`tel:${dest.contact_number}`}
            className="evac-action-btn call-btn"
          >
            <Phone size={13} /> Call Camp Manager ({dest.contact_number})
          </a>
        )}
        <button
          onClick={() => onFocusShelter && onFocusShelter(dest)}
          className="evac-action-btn focus-btn"
        >
          <MapPin size={13} /> Center on Camp
        </button>
      </div>
    </div>
  );
}
