import { X, Home, Users, Phone, MapPin, Navigation, Edit3 } from 'lucide-react';

export default function ShelterDetailModal({
  isOpen,
  onClose,
  shelter,
  user,
  onPlanRoute,
  onOpenOccupancyEdit
}) {
  if (!isOpen || !shelter) return null;

  const capacity = shelter.capacity || 100;
  const occupied = shelter.occupied || 0;
  const available = Math.max(0, capacity - occupied);
  const occupancyPct = Math.round((occupied / capacity) * 100);

  const isAuthorityOrVolunteer = user && (user.role === 'Authority_Admin' || user.role === 'Volunteer');

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="shelter-detail-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="shelter-icon-badge">
              <Home size={20} color="#30D158" />
            </div>
            <div>
              <h2 className="auth-title" style={{ margin: 0 }}>{shelter.name}</h2>
              <span className="auth-subtitle">District: {shelter.district} &bull; Relief Camp ID #{shelter.id}</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Occupancy Progress Strip */}
        <div className="shelter-occupancy-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Users size={14} color="var(--accent-green)" />
              <span style={{ fontSize: '12px', fontWeight: '800', color: 'var(--text-primary)' }}>
                Live Bed Capacity & Occupancy
              </span>
            </div>
            <span style={{ fontSize: '11.5px', fontWeight: '800', color: available > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {occupied} / {capacity} Beds ({occupancyPct}%)
            </span>
          </div>

          <div className="shelter-occupancy-bar-bg">
            <div
              className="shelter-occupancy-bar-fill"
              style={{
                width: `${Math.min(100, occupancyPct)}%`,
                backgroundColor: occupancyPct > 90 ? '#EF4444' : occupancyPct > 70 ? '#F59E0B' : '#30D158'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            <span>Available Spots: <strong style={{ color: 'var(--text-primary)' }}>{available}</strong></span>
            <span>Status: <strong style={{ color: available > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{available > 0 ? 'Accepting Citizens' : 'At Full Capacity'}</strong></span>
          </div>
        </div>

        {/* Shelter Meta Details */}
        <div className="shelter-meta-grid">
          <div className="shelter-meta-box">
            <span className="shelter-meta-label"><MapPin size={11} color="var(--accent)" /> Coordinates</span>
            <span className="shelter-meta-val">({shelter.lat.toFixed(4)}°N, {shelter.lng.toFixed(4)}°E)</span>
          </div>
          {shelter.distance_km !== undefined && (
            <div className="shelter-meta-box">
              <span className="shelter-meta-label"><Navigation size={11} color="var(--accent)" /> Distance from Home</span>
              <span className="shelter-meta-val">~{shelter.distance_km} km</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
          <button
            onClick={() => {
              onClose();
              if (onPlanRoute) onPlanRoute(shelter);
            }}
            className="ios-button shelter-plan-route-btn"
          >
            <Navigation size={15} /> Plan Safe Evacuation Route to this Shelter
          </button>

          <div style={{ display: 'flex', gap: '10px' }}>
            {shelter.contact_number && (
              <a
                href={`tel:${shelter.contact_number}`}
                className="ios-button shelter-call-btn"
                style={{ flex: 1, textDecoration: 'none' }}
              >
                <Phone size={14} /> Call Camp ({shelter.contact_number})
              </a>
            )}

            {isAuthorityOrVolunteer && (
              <button
                onClick={() => {
                  onClose();
                  if (onOpenOccupancyEdit) onOpenOccupancyEdit(shelter);
                }}
                className="ios-button shelter-edit-btn"
                style={{ flex: 1 }}
              >
                <Edit3 size={14} /> Update Occupancy
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
