import { useState } from 'react';
import { Radio, Navigation, Home, X } from 'lucide-react';

export default function BroadcastAlertBanner({ broadcasts, user, onFocusAlert, onFindShelter }) {
  const [isDismissed, setIsDismissed] = useState(false);
  const [langTab, setLangTab] = useState('en'); // 'en' or 'ml'

  if (!broadcasts || broadcasts.length === 0 || isDismissed) return null;

  const currentAlert = broadcasts[0];
  if (!currentAlert) return null;

  // Calculate distance from user to hazard if user coordinates available
  let distanceKm = null;
  if (user?.lat && user?.lng && currentAlert.lat && currentAlert.lng) {
    const R = 6371; // km
    const dLat = (currentAlert.lat - user.lat) * (Math.PI / 180);
    const dLng = (currentAlert.lng - user.lng) * (Math.PI / 180);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(user.lat * (Math.PI / 180)) *
        Math.cos(currentAlert.lat * (Math.PI / 180)) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    distanceKm = roundToOneDecimal(R * c);
  }

  function roundToOneDecimal(num) {
    return Math.round(num * 10) / 10;
  }

  const isInsideDangerZone = distanceKm !== null && distanceKm <= currentAlert.radius_km;

  return (
    <div className="public-broadcast-banner ios-glass">
      {/* Alert Header Row */}
      <div className="public-banner-top-row">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="public-banner-icon-pulse">
            <Radio size={16} color="#FFF" />
          </div>
          <span className="public-banner-tag">
            {isInsideDangerZone ? '🚨 CRITICAL EVACUATION ORDER (INSIDE PERIMETER)' : '⚠️ ACTIVE STATE EMERGENCY BROADCAST'}
          </span>
          <span className="public-banner-time">
            {new Date(currentAlert.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="public-banner-lang-toggle">
            <button
              className={`banner-lang-btn ${langTab === 'en' ? 'active' : ''}`}
              onClick={() => setLangTab('en')}
            >
              EN
            </button>
            <button
              className={`banner-lang-btn ${langTab === 'ml' ? 'active' : ''}`}
              onClick={() => setLangTab('ml')}
            >
              മലയാളം
            </button>
          </div>

          <button onClick={() => setIsDismissed(true)} className="public-banner-dismiss-btn" title="Dismiss banner">
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Main Alert Message */}
      <div className="public-banner-body">
        <p className={`public-banner-text ${langTab === 'ml' ? 'ml-font' : ''}`}>
          {langTab === 'en' ? currentAlert.alert_en : currentAlert.alert_ml}
        </p>

        {/* Distance & Action Row */}
        <div className="public-banner-footer-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="public-banner-coords-pill">
              📍 Hazard Epicenter: ({currentAlert.lat.toFixed(3)}°N, {currentAlert.lng.toFixed(3)}°E) &bull; {currentAlert.radius_km}km Radius
            </span>
            {distanceKm !== null && (
              <span className={`public-banner-dist-pill ${isInsideDangerZone ? 'danger' : 'safe'}`}>
                {isInsideDangerZone ? `⚠️ You are ${distanceKm} km from epicenter (INSIDE DANGER ZONE)` : `Distance from home: ~${distanceKm} km`}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => onFocusAlert && onFocusAlert(currentAlert)}
              className="public-banner-action-btn map-btn"
            >
              <Navigation size={12} /> View Hazard on Map
            </button>
            <button
              onClick={() => onFindShelter && onFindShelter()}
              className="public-banner-action-btn shelter-btn"
            >
              <Home size={12} /> Route to Relief Shelter
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
