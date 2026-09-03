import { useState } from 'react';
import { X, Save, AlertTriangle, Home } from 'lucide-react';
import api from '../services/api';

export default function ShelterOccupancyModal({
  isOpen,
  onClose,
  shelter,
  triggerToast,
  onOccupancyUpdated
}) {
  const [occupied, setOccupied] = useState(shelter?.occupied ?? 0);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen || !shelter) return null;

  const capacity = shelter.capacity || 100;
  const available = Math.max(0, capacity - occupied);
  const occupancyPct = Math.round((occupied / capacity) * 100);

  const handleSave = async (e) => {
    e.preventDefault();
    setUpdating(true);
    setError('');

    try {
      const res = await api.post('/api/shelters/update-occupancy', {
        shelter_id: shelter.id,
        occupied: parseInt(occupied)
      });

      if (res.data.success) {
        triggerToast(`✓ Occupancy for '${shelter.name}' updated to ${res.data.occupied}/${capacity} beds!`, 'success');
        if (onOccupancyUpdated) onOccupancyUpdated(res.data);
        onClose();
      } else {
        setError(res.data.error || "Update failed.");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update camp occupancy.");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="auth-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="shelter-icon-badge">
              <Home size={18} color="#30D158" />
            </div>
            <div>
              <h2 className="auth-title">Update Camp Occupancy</h2>
              <span className="auth-subtitle">{shelter.name} ({shelter.district})</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="auth-error-banner">
            <AlertTriangle size={14} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="auth-form">
          <div className="shelter-occupancy-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-secondary)' }}>
                Total Camp Capacity: <strong style={{ color: 'var(--text-primary)' }}>{capacity} Beds</strong>
              </span>
              <span style={{ fontSize: '12px', fontWeight: '800', color: available > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {occupied} / {capacity} ({occupancyPct}%)
              </span>
            </div>

            <input
              type="range"
              min="0"
              max={capacity}
              value={occupied}
              onChange={(e) => setOccupied(parseInt(e.target.value))}
              className="ios-slider"
            />
          </div>

          <div className="auth-field-group">
            <label className="auth-label">Occupied Beds (Numerical Count)</label>
            <input
              type="number"
              min="0"
              max={capacity}
              value={occupied}
              onChange={(e) => setOccupied(Math.max(0, Math.min(capacity, parseInt(e.target.value) || 0)))}
              className="auth-input"
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'var(--bg-surface)', borderRadius: '12px', fontSize: '11px' }}>
            <span>Remaining Open Spots:</span>
            <strong style={{ color: 'var(--accent-green)' }}>{available} Beds Available</strong>
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
            <button
              type="button"
              onClick={onClose}
              className="ios-button"
              style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updating}
              className="ios-button"
              style={{ flex: 2, background: 'linear-gradient(135deg, #30D158 0%, #16A34A 100%)', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
            >
              <Save size={14} />
              {updating ? 'Saving...' : 'Update Live Bed Count'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
