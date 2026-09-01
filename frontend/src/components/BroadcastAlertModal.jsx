import { useState, useEffect } from 'react';
import { X, Send, Radio, AlertTriangle, Users, MapPin, Sparkles, Globe } from 'lucide-react';
import axios from 'axios';

export default function BroadcastAlertModal({ isOpen, onClose, cluster, token, triggerToast, onBroadcastSuccess }) {
  const [radiusKm, setRadiusKm] = useState(5.0);
  const [targetCount, setTargetCount] = useState(0);
  const [alertEn, setAlertEn] = useState('');
  const [alertMl, setAlertMl] = useState('');
  const [synthesisSource, setSynthesisSource] = useState('');
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [transmitting, setTransmitting] = useState(false);
  const [error, setError] = useState('');

  const lat = cluster?.lat ?? 11.5542;
  const lng = cluster?.lng ?? 76.1308;
  const hazardType = cluster?.primary_hazard_type ?? 'slope_movement';
  const severity = cluster?.max_severity ?? cluster?.avg_severity ?? 4;

  // Fetch bilingual preview whenever cluster or radius changes
  useEffect(() => {
    if (!isOpen || !token) return;

    let isMounted = true;
    const timer = setTimeout(() => {
      setLoadingPreview(true);
      setError('');

      axios.post('http://127.0.0.1:5000/api/alerts/preview', {
        lat,
        lng,
        radius_km: radiusKm,
        hazard_type: hazardType,
        severity: severity
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(res => {
          if (isMounted && res.data.success) {
            setAlertEn(res.data.alert_en);
            setAlertMl(res.data.alert_ml);
            setTargetCount(res.data.target_citizens_count);
            setSynthesisSource(res.data.synthesis_source);
          }
        })
        .catch(err => {
          if (isMounted) {
            console.error("Alert preview error:", err);
            setError("Could not generate alert preview. Check server connectivity.");
          }
        })
        .finally(() => {
          if (isMounted) setLoadingPreview(false);
        });
    }, 250);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [isOpen, radiusKm, hazardType, lat, lng, token]);

  if (!isOpen) return null;

  const handleTransmit = async (e) => {
    e.preventDefault();
    if (!alertEn.trim() || !alertMl.trim()) {
      setError("English and Malayalam alert messages cannot be empty.");
      return;
    }

    setTransmitting(true);
    setError('');

    try {
      const res = await axios.post('http://127.0.0.1:5000/api/alerts/broadcast', {
        lat,
        lng,
        radius_km: radiusKm,
        hazard_type: hazardType,
        alert_en: alertEn.trim(),
        alert_ml: alertMl.trim()
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.data.success) {
        triggerToast(`✓ Emergency Broadcast transmitted to ${res.data.recipients_count} citizens via SMS gateway!`, "success");
        if (onBroadcastSuccess) onBroadcastSuccess(res.data);
        onClose();
      } else {
        setError(res.data.error || "Broadcast transmission failed.");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Broadcast gateway request exception.");
    } finally {
      setTransmitting(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="broadcast-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div>
            <h2 className="auth-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Radio size={20} color="var(--accent-red)" className="pulse-anim" />
              GEO-FENCED <span style={{ color: 'var(--accent-red)' }}>EMERGENCY BROADCAST</span>
            </h2>
            <p className="auth-subtitle">CAP v1.2 Standard / ITU-T X.1303 Telecom Dispatch Engine</p>
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

        <form onSubmit={handleTransmit} className="broadcast-form">
          {/* Geofence Perimeter Radius Controls */}
          <div className="broadcast-meta-box">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <MapPin size={14} color="var(--accent)" />
                <span style={{ fontSize: '11.5px', fontWeight: '800', color: 'var(--text-primary)' }}>
                  Epicenter GPS: ({lat.toFixed(4)}°N, {lng.toFixed(4)}°E)
                </span>
              </div>
              <span className="target-citizens-pill">
                <Users size={12} /> {loadingPreview ? 'Estimating...' : `${targetCount} Registered Citizens`}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label className="auth-label">Evacuation & Alert Radius</label>
              <span style={{ fontSize: '12px', fontWeight: '800', color: 'var(--accent-red)' }}>
                {radiusKm.toFixed(1)} km Perimeter
              </span>
            </div>
            <input
              type="range"
              min="1.0"
              max="25.0"
              step="0.5"
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseFloat(e.target.value))}
              className="ios-slider broadcast-radius-slider"
            />
          </div>

          {/* Bilingual Synthesis Badge */}
          <div className="synthesis-badge-row">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Globe size={13} color="var(--accent)" />
              <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Bilingual Multi-Channel Alert Copy
              </span>
            </div>
            <span className="synthesis-source-tag">
              <Sparkles size={10} /> {synthesisSource === 'ollama-llama3.2' ? 'Synthesized via Ollama LLaMA 3.2' : 'Verified KSDMA CAP Template'}
            </span>
          </div>

          {/* English Alert Copy Editor */}
          <div className="auth-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="auth-label">English Emergency Alert (SMS & CAP en-IN)</label>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{alertEn.length} chars</span>
            </div>
            <textarea
              rows={3}
              value={alertEn}
              onChange={(e) => setAlertEn(e.target.value)}
              className="auth-input report-textarea broadcast-textarea"
              required
            />
          </div>

          {/* Malayalam Alert Copy Editor */}
          <div className="auth-field-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="auth-label">Malayalam Emergency Alert (SMS & CAP ml-IN / മലയാളം)</label>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{alertMl.length} chars</span>
            </div>
            <textarea
              rows={3}
              value={alertMl}
              onChange={(e) => setAlertMl(e.target.value)}
              className="auth-input report-textarea broadcast-textarea ml-text"
              required
            />
          </div>

          {/* Broadcast Action Buttons */}
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
              disabled={transmitting || loadingPreview}
              className="ios-button broadcast-submit-btn"
              style={{ flex: 2 }}
            >
              <Send size={14} />
              {transmitting ? 'Transmitting to Telecom Gateways...' : `Transmit Geofenced SMS Blast (${targetCount} Citizens)`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
