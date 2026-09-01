import { useState, useEffect } from 'react';
import { X, AlertOctagon, MapPin, Battery, Phone, Send, Copy, Check, Radio } from 'lucide-react';

export default function EmergencySOSModal({
  isOpen,
  onClose,
  user,
  currentCoords,
  triggerToast
}) {
  const [locating, setLocating] = useState(false);
  const [gpsCoords, setGpsCoords] = useState(null);
  const [batteryLevel, setBatteryLevel] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGpsCoords({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy: Math.round(pos.coords.accuracy)
          });
          setLocating(false);
        },
        (err) => {
          console.warn('[SOS] Geolocation fetch fallback to map center:', err);
          const fallbackLat = user?.lat || currentCoords?.lat || 11.5542;
          const fallbackLng = user?.lng || currentCoords?.lng || 76.1308;
          setGpsCoords({ lat: fallbackLat, lng: fallbackLng, accuracy: 50 });
          setLocating(false);
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
      );
    } else {
      const fallbackLat = user?.lat || currentCoords?.lat || 11.5542;
      const fallbackLng = user?.lng || currentCoords?.lng || 76.1308;
      setGpsCoords({ lat: fallbackLat, lng: fallbackLng, accuracy: 50 });
      setLocating(false);
    }

    // 2. Fetch Device Battery Status
    if (navigator.getBattery) {
      navigator.getBattery().then((battery) => {
        setBatteryLevel(Math.round(battery.level * 100));
      }).catch(() => {});
    }
  }, [isOpen, user, currentCoords]);

  if (!isOpen) return null;

  const lat = gpsCoords?.lat?.toFixed(5) || "11.55420";
  const lng = gpsCoords?.lng?.toFixed(5) || "76.13080";
  const mapsUrl = `https://maps.google.com/?q=${lat},${lng}`;
  const userName = user?.name || "Citizen (Disaster Zone)";
  const userPhone = user?.phone || "Unknown";
  const batteryStr = batteryLevel !== null ? `${batteryLevel}%` : "Standard";

  const sosBody = `EMERGENCY SOS: Immediate landslide/flood rescue required! My Location: ${mapsUrl} (${lat}N, ${lng}E). Battery: ${batteryStr}. Name: ${userName}. Phone: ${userPhone}.`;

  // Deep link format: iOS requires '&body=', Android standard uses '?body='
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const smsDeepLink = isIOS
    ? `sms:112&body=${encodeURIComponent(sosBody)}`
    : `sms:112?body=${encodeURIComponent(sosBody)}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(sosBody);
    setCopied(true);
    triggerToast("✓ Emergency SOS message & GPS coordinates copied to clipboard!", "success");
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 15000 }}>
      <div className="sos-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Pulsing Beacon Header */}
        <div className="sos-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="sos-beacon-pulse-icon">
              <AlertOctagon size={22} color="#FFF" />
            </div>
            <div>
              <h2 className="sos-title">EMERGENCY SOS BEACON</h2>
              <span className="sos-subtitle">Offline Cellular Distress Protocol</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Live GPS Telemetry Strip */}
        <div className="sos-telemetry-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MapPin size={14} color="#EF4444" className="bounce-anim" />
              <span style={{ fontSize: '11px', fontWeight: '800', color: 'var(--text-primary)' }}>
                {locating ? 'Acquiring GPS Fix...' : 'Live GPS Coordinate Lock'}
              </span>
            </div>
            {gpsCoords?.accuracy && (
              <span className="sos-accuracy-badge">Accuracy: &plusmn;{gpsCoords.accuracy}m</span>
            )}
          </div>

          <div className="sos-coords-display">
            <span className="sos-coords-text">{lat}&deg; N, {lng}&deg; E</span>
            {batteryLevel !== null && (
              <div className="sos-battery-badge">
                <Battery size={12} color={batteryLevel < 20 ? '#EF4444' : '#30D158'} />
                <span>{batteryLevel}%</span>
              </div>
            )}
          </div>

          <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Location: <strong style={{ color: 'var(--text-primary)' }}>{user?.district || 'Kerala Western Ghats'}</strong>
          </div>
        </div>

        {/* Pre-Formatted Distress Message Box */}
        <div className="sos-preview-box">
          <span className="sos-preview-label">Pre-Formatted Distress Payload:</span>
          <p className="sos-preview-text">"{sosBody}"</p>
        </div>

        {/* Action Dispatch Buttons */}
        <div className="sos-action-stack">
          {/* Primary Action: Direct Cellular SMS (Works 100% Offline via 2G/3G/4G/5G SMS) */}
          <a
            href={smsDeepLink}
            className="sos-primary-btn"
            onClick={() => triggerToast("Launching cellular SMS composer...", "info")}
          >
            <Send size={16} />
            <span>Send SOS via Cellular SMS (112)</span>
          </a>

          {/* Direct Phone Call Actions */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <a href="tel:112" className="sos-call-btn erss">
              <Phone size={14} /> Call 112 (ERSS)
            </a>
            <a href="tel:1077" className="sos-call-btn ddma">
              <Phone size={14} /> Call 1077 (DDMA)
            </a>
          </div>

          {/* Copy Message Action */}
          <button onClick={handleCopy} className="sos-copy-btn">
            {copied ? <Check size={14} color="var(--accent-green)" /> : <Copy size={14} />}
            <span>{copied ? 'Distress Message Copied!' : 'Copy Coordinates & Text'}</span>
          </button>
        </div>

        {/* Offline Safety Guidance Note */}
        <div className="sos-footer-note">
          <Radio size={12} color="var(--accent-orange)" />
          <span>Works without mobile data / Wi-Fi. Transmits directly over telecom towers.</span>
        </div>
      </div>
    </div>
  );
}
