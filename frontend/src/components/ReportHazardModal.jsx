import { useState } from 'react';
import { X, AlertTriangle, ShieldAlert, MapPin, Send, AlertOctagon, Waves, Mountain, Construction, Zap, Camera, Sparkles } from 'lucide-react';
import api from '../services/api';

const HAZARD_CATEGORIES = [
  { id: 'mud_crack', label: 'Mud Crack / Fissure', icon: Zap, color: '#F59E0B', desc: 'Tension cracks, soil displacement, slope fractures' },
  { id: 'stream_overflow', label: 'Stream Overflow', icon: Waves, color: '#38BDF8', desc: 'Raging culverts, drainage blockage, flash water torrents' },
  { id: 'rockfall', label: 'Rockfall / Debris Roll', icon: Mountain, color: '#EC4899', desc: 'Falling boulders, scree slope tumble, loose rock masses' },
  { id: 'blocked_road', label: 'Blocked Roadway', icon: Construction, color: '#F97316', desc: 'Debris blocking transit corridors, downed tree/mud slide' },
  { id: 'slope_movement', label: 'Slope Movement / Creep', icon: AlertOctagon, color: '#EF4444', desc: 'Active hill subsidence, creeping mud mass, wall bulge' },
];

const SEVERITY_LEVELS = [
  { level: 1, label: 'Minor Advisory', color: '#30D158', desc: 'Small surface tension cracks or shallow runoff' },
  { level: 2, label: 'Moderate Caution', color: '#38BDF8', desc: 'Noticeable soil displacement or overflowing drains' },
  { level: 3, label: 'High Threat', color: '#FF9F0A', desc: 'Road partially blocked or expanding fissures' },
  { level: 4, label: 'Severe Hazard', color: '#FF453A', desc: 'Impending slope collapse or major road cut-off' },
  { level: 5, label: 'Catastrophic / Life Threat', color: '#9B59B6', desc: 'Active mass wasting, debris torrent requiring instant evacuation' }
];

export default function ReportHazardModal({ isOpen, onClose, coordinates, user, token, onReportSuccess, triggerToast }) {
  const [hazardType, setHazardType] = useState('mud_crack');
  const [severity, setSeverity] = useState(3);
  const [description, setDescription] = useState('');
  const [photoBase64, setPhotoBase64] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [cvFeedback, setCvFeedback] = useState(null);
  const [cvAnalyzing, setCvAnalyzing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const lat = coordinates?.lat ? parseFloat(coordinates.lat.toFixed(4)) : 11.5510;
  const lng = coordinates?.lng ? parseFloat(coordinates.lng.toFixed(4)) : 76.1280;
  const selectedSeverityObj = SEVERITY_LEVELS.find(s => s.level === severity) || SEVERITY_LEVELS[2];

  const handlePhotoSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const b64 = event.target.result;
      setPhotoBase64(b64);
      setPhotoPreview(b64);

      // Trigger background CV verification preview
      setCvAnalyzing(true);
      setCvFeedback(null);
      try {
        const res = await api.post('/api/vision/analyze', {
          image: b64,
          hazard_type: hazardType
        });
        if (res.data.success) {
          setCvFeedback(res.data.analysis);
        }
      } catch {
        console.log("CV pre-analysis skipped.");
      } finally {
        setCvAnalyzing(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!token && !localStorage.getItem('terrarisk_token')) {
      setError('You must be signed in to submit hazard reports.');
      return;
    }

    if (!description.trim()) {
      setError('Please provide a brief description of the observed hazard.');
      return;
    }

    setLoading(true);
    try {
      const res = await api.post('/api/incidents/report', {
        hazard_type: hazardType,
        lat: lat,
        lng: lng,
        severity: severity,
        description: description.trim(),
        image: photoBase64
      });

      if (res.data.success) {
        const clusterMsg = res.data.is_clustered
          ? '✓ Report auto-clustered with nearby sector reports (500m).'
          : '✓ New spatial hazard cluster generated.';
        triggerToast(clusterMsg, 'success');
        onReportSuccess(res.data);
        onClose();
      } else {
        setError(res.data.error || 'Could not submit report.');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Submission failed. Check network connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="report-hazard-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div>
            <h2 className="auth-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={20} color="var(--accent)" />
              REPORT <span style={{ color: 'var(--accent)' }}>HAZARD</span>
            </h2>
            <p className="auth-subtitle">Real-time Crowd-Sourced Field Telemetry</p>
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

        <form onSubmit={handleSubmit} className="report-hazard-form">
          {/* Coordinates & Reporter Profile Pill */}
          <div className="report-hazard-meta-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MapPin size={13} color="var(--accent)" />
              <span style={{ fontSize: '11.5px', fontWeight: '550', color: 'var(--text-primary)' }}>
                GPS Locked: ({lat}°N, {lng}°E)
              </span>
            </div>
            <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', fontWeight: '500' }}>
              Reporter: <b style={{ color: 'var(--accent-green)' }}>{user?.name?.split(' ')[0] || 'Citizen'}</b> {user?.is_verified || user?.role === 'Authority_Admin' ? <span style={{ color: '#30D158' }}>✓ Verified</span> : <span style={{ color: 'var(--text-secondary)' }}>• Active</span>}
            </div>
          </div>

          {/* Hazard Category Grid */}
          <div className="auth-field-group">
            <label className="auth-label">Select Hazard Category</label>
            <div className="hazard-category-grid">
              {HAZARD_CATEGORIES.map((cat) => {
                const IconComponent = cat.icon;
                const isSelected = hazardType === cat.id;
                return (
                  <div
                    key={cat.id}
                    onClick={() => setHazardType(cat.id)}
                    className={`hazard-cat-card ${isSelected ? 'selected' : ''}`}
                    style={{ borderColor: isSelected ? cat.color : 'var(--border-color)' }}
                  >
                    <div className="hazard-cat-icon-frame" style={{ backgroundColor: `${cat.color}20`, color: cat.color }}>
                      <IconComponent size={18} />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span className="hazard-cat-title" style={{ color: isSelected ? cat.color : 'var(--text-primary)' }}>
                        {cat.label}
                      </span>
                      <span className="hazard-cat-desc">{cat.desc}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Severity Slider (1 to 5) */}
          <div className="auth-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label className="auth-label">Severity Level (1 to 5)</label>
              <span className="severity-badge-pill" style={{ backgroundColor: `${selectedSeverityObj.color}25`, color: selectedSeverityObj.color, borderColor: selectedSeverityObj.color }}>
                Level {severity}: {selectedSeverityObj.label}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value={severity}
              onChange={(e) => setSeverity(parseInt(e.target.value))}
              className="ios-slider severity-slider"
              style={{ accentColor: selectedSeverityObj.color }}
            />
            <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {selectedSeverityObj.desc}
            </span>
          </div>

          {/* Photo Upload & AI Vision Preview */}
          <div className="auth-field-group">
            <label className="auth-label">Attach Photo (AI Verified)</label>
            <div className="photo-upload-container">
              <label className="photo-upload-btn">
                <Camera size={16} />
                <span>{photoPreview ? "Change Photo" : "Upload Field Photo"}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoSelect}
                  style={{ display: 'none' }}
                />
              </label>

              {cvAnalyzing && (
                <span style={{ fontSize: '11px', color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Sparkles size={13} className="spin-anim" />
                  Analyzing photo with Computer Vision Brain...
                </span>
              )}

              {cvFeedback && (
                <div className={`cv-feedback-pill ${cvFeedback.is_genuine_hazard ? 'genuine' : 'warning'}`}>
                  <Sparkles size={13} />
                  <span>
                    {cvFeedback.is_genuine_hazard ? '✓ Verified Hazard' : '⚠️ Non-Hazard Scene'}: {Math.round(cvFeedback.confidence_score * 100)}% ({cvFeedback.detected_hazard.replace(/_/g, ' ')})
                  </span>
                </div>
              )}
            </div>

            {cvFeedback?.ai_summary && (
              <div style={{ fontSize: '11px', color: cvFeedback.is_genuine_hazard ? 'var(--text-secondary)' : '#FF453A', padding: '4px 8px', background: cvFeedback.is_genuine_hazard ? 'rgba(255,255,255,0.04)' : 'rgba(239,68,68,0.1)', borderRadius: '8px', border: `1px solid ${cvFeedback.is_genuine_hazard ? 'var(--border-color)' : 'rgba(239,68,68,0.2)'}`, marginTop: '4px' }}>
                <strong>AI Assessment:</strong> {cvFeedback.ai_summary}
              </div>
            )}

            {photoPreview && (
              <div className="photo-preview-box">
                <img src={photoPreview} alt="Hazard Preview" />
                <button type="button" className="btn-remove-photo" onClick={() => { setPhotoPreview(null); setPhotoBase64(null); setCvFeedback(null); }}>
                  <X size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Incident Description */}
          <div className="auth-field-group">
            <label className="auth-label">Field Description & Observations *</label>
            <textarea
              rows={2}
              placeholder="e.g. Rapidly expanding soil cracks along road shoulder with water seeping from escarpment..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="auth-input report-textarea"
              required
            />
          </div>

          {/* Submission Action */}
          <button type="submit" className="ios-button auth-submit-btn report-submit-btn" disabled={loading}>
            <Send size={14} />
            {loading ? 'Transmitting to AI Cluster Engine...' : 'Submit Incident Report'}
          </button>
        </form>
      </div>
    </div>
  );
}
