import { useState, useEffect } from 'react';
import { X, AlertTriangle, ShieldAlert, MapPin, Send, AlertOctagon, Waves, Mountain, Construction, Zap, Camera, Sparkles, Navigation, CheckCircle2, RefreshCw } from 'lucide-react';
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

const compressImage = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (e) => {
      const img = new Image();
      img.src = e.target.result;
      img.onload = () => {
        let { width, height } = img;
        const maxDim = 1200;
        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = Math.round((height * maxDim) / width);
            width = maxDim;
          } else {
            width = Math.round((width * maxDim) / height);
            height = maxDim;
          }
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        const compressedB64 = canvas.toDataURL('image/jpeg', 0.8);
        resolve(compressedB64);
      };
      img.onerror = () => reject(new Error('Failed to load image for compression'));
    };
    reader.onerror = () => reject(new Error('Failed to read image file'));
  });
};

export default function ReportHazardModal({ isOpen, onClose, coordinates, user, token, onPickOnMap, onReportSuccess, triggerToast }) {
  const [hazardType, setHazardType] = useState('mud_crack');
  const [severity, setSeverity] = useState(3);
  const [description, setDescription] = useState('');
  const [photoBase64, setPhotoBase64] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [cvFeedback, setCvFeedback] = useState(null);
  const [cvAnalyzing, setCvAnalyzing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Auto-location telemetry state to guarantee report credibility
  const [reportLat, setReportLat] = useState(coordinates?.lat ? parseFloat(coordinates.lat.toFixed(5)) : 11.5510);
  const [reportLng, setReportLng] = useState(coordinates?.lng ? parseFloat(coordinates.lng.toFixed(5)) : 76.1280);
  const [isLocating, setIsLocating] = useState(false);
  const [isGpsVerified, setIsGpsVerified] = useState(false);
  const [gpsAccuracy, setGpsAccuracy] = useState(null);

  // Automatically fetch live GPS on modal open to guarantee incident credibility
  useEffect(() => {
    if (!isOpen) return;

    if (navigator.geolocation) {
      setIsLocating(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const latVal = parseFloat(pos.coords.latitude.toFixed(5));
          const lngVal = parseFloat(pos.coords.longitude.toFixed(5));
          const acc = Math.round(pos.coords.accuracy);
          setReportLat(latVal);
          setReportLng(lngVal);
          setGpsAccuracy(acc);
          setIsGpsVerified(true);
          setIsLocating(false);
        },
        (err) => {
          setIsLocating(false);
          console.warn("Auto GPS fetch notice:", err.message);
          if (coordinates?.lat && coordinates?.lng) {
            setReportLat(parseFloat(coordinates.lat.toFixed(5)));
            setReportLng(parseFloat(coordinates.lng.toFixed(5)));
            if (coordinates.isGps) {
              setIsGpsVerified(true);
              setGpsAccuracy(coordinates.accuracy || 15);
            }
          }
        },
        { enableHighAccuracy: true, timeout: 9000, maximumAge: 0 }
      );
    } else if (coordinates?.lat && coordinates?.lng) {
      setReportLat(parseFloat(coordinates.lat.toFixed(5)));
      setReportLng(parseFloat(coordinates.lng.toFixed(5)));
    }
  }, [isOpen]);

  // Sync if parent updates picked pin manually
  useEffect(() => {
    if (coordinates?.lat && coordinates?.lng && !isLocating) {
      setReportLat(parseFloat(coordinates.lat.toFixed(5)));
      setReportLng(parseFloat(coordinates.lng.toFixed(5)));
      if (coordinates.isGps) {
        setIsGpsVerified(true);
        setGpsAccuracy(coordinates.accuracy || 10);
      }
    }
  }, [coordinates?.lat, coordinates?.lng]);

  if (!isOpen) return null;

  const lat = reportLat;
  const lng = reportLng;
  const selectedSeverityObj = SEVERITY_LEVELS.find(s => s.level === severity) || SEVERITY_LEVELS[2];

  const handlePhotoSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const b64 = await compressImage(file);
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
        if (res.data?.success) {
          setCvFeedback(res.data.analysis);
        }
      } catch {
        console.log("CV pre-analysis skipped.");
      } finally {
        setCvAnalyzing(false);
      }
    } catch (err) {
      console.error("Image compression error:", err);
      setError("Failed to process image. Please try another photo.");
    }
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
        image: photoBase64,
        is_gps_verified: isGpsVerified,
        gps_accuracy: gpsAccuracy
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
          {/* Coordinates & Reporter Profile Pill with Auto-Location Credibility */}
          <div className="report-hazard-meta-banner" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '10px 12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <MapPin size={13} color="var(--accent)" />
                <span style={{ fontSize: '11.5px', fontWeight: '600', color: 'var(--text-primary)' }}>
                  {isGpsVerified ? 'GPS Location:' : 'Target Location:'} ({lat}°N, {lng}°E)
                </span>
                {onPickOnMap && (
                  <button
                    type="button"
                    onClick={onPickOnMap}
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'rgba(56, 189, 248, 0.12)',
                      color: '#38BDF8',
                      cursor: 'pointer',
                      fontWeight: '600',
                      marginLeft: '4px'
                    }}
                    title="Pick a different location by clicking on the map"
                  >
                    📍 Adjust on Map
                  </button>
                )}
              </div>
              <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                Reporter: <b style={{ color: 'var(--accent-green)' }}>{user?.name?.split(' ')[0] || 'Citizen'}</b> {user?.is_verified || user?.role === 'Authority_Admin' ? <span style={{ color: '#30D158' }}>✓ Verified</span> : <span style={{ color: 'var(--text-secondary)' }}>• Active</span>}
              </div>
            </div>

            {/* Auto-Location Credibility Guarantee Banner */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: isLocating ? 'rgba(56, 189, 248, 0.08)' : isGpsVerified ? 'rgba(48, 209, 88, 0.12)' : 'rgba(245, 158, 11, 0.08)',
              border: `1px solid ${isLocating ? 'rgba(56, 189, 248, 0.25)' : isGpsVerified ? 'rgba(48, 209, 88, 0.35)' : 'rgba(245, 158, 11, 0.25)'}`,
              borderRadius: '8px',
              padding: '6px 10px',
              fontSize: '11px',
              fontWeight: '550'
            }}>
              {isLocating ? (
                <>
                  <RefreshCw size={12} className="auth-spinner" style={{ color: '#38BDF8' }} />
                  <span style={{ color: '#38BDF8' }}>🛰️ Auto-fetching live GPS to guarantee incident credibility...</span>
                </>
              ) : isGpsVerified ? (
                <>
                  <CheckCircle2 size={13} style={{ color: '#30D158' }} />
                  <span style={{ color: '#30D158' }}>
                    🛰️ Live GPS Auto-Verified (High Credibility{gpsAccuracy ? ` • ±${gpsAccuracy}m precision` : ''})
                  </span>
                </>
              ) : (
                <>
                  <Navigation size={12} style={{ color: '#F59E0B' }} />
                  <span style={{ color: '#F59E0B' }}>📍 Pinned Location ({lat}°, {lng}°)</span>
                </>
              )}
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
                <div className={`cv-keyword-badge-container ${cvFeedback.is_genuine_hazard ? 'genuine' : 'warning'}`}>
                  <div className="cv-keyword-pill-header">
                    <span className="cv-keyword-code">
                      {cvFeedback.keyword || (cvFeedback.is_genuine_hazard ? 'INCIDENT_VERIFIED_TRUE' : 'INCIDENT_VERIFIED_FALSE')}
                    </span>
                    <span className={`cv-keyword-verdict ${cvFeedback.is_genuine_hazard ? 'genuine' : 'warning'}`}>
                      {cvFeedback.is_genuine_hazard ? '✓ INCIDENT CONFIRMED' : '⚠️ INCIDENT REJECTED'}
                    </span>
                    <span className="cv-keyword-conf">
                      {Math.round(cvFeedback.confidence_score * 100)}% Confidence
                    </span>
                  </div>
                  <div className="cv-keyword-label-row">
                    <Sparkles size={13} />
                    <span>{cvFeedback.status_text || (cvFeedback.is_genuine_hazard ? 'Disaster Hazard Verified' : 'Non-Hazard Scene')}</span>
                  </div>
                </div>
              )}
            </div>

            {cvFeedback?.ai_summary && (
              <div className={`cv-summary-card ${cvFeedback.is_genuine_hazard ? 'genuine' : 'warning'}`}>
                <strong>Geotechnical Assessment:</strong> {cvFeedback.ai_summary}
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
