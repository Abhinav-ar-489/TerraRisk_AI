import { MapPin, AlertTriangle, Navigation, PhoneCall, Menu, Loader2 } from 'lucide-react';

export default function MobileBottomNav({
  onCheckSafety,
  onReportHazard,
  onSafeRoute,
  onOpenHelplines,
  onOpenMenu,
  planningRoute = false,
  checkingSafety = false,
  deviceCoords = null,
}) {
  return (
    <nav className="mobile-bottom-nav ios-glass" aria-label="Emergency Quick Actions">
      <button
        type="button"
        className={`mob-nav-btn ${deviceCoords ? 'active' : ''}`}
        onClick={onCheckSafety}
        disabled={checkingSafety}
        title="Check Local Safety & Near Me Hazards"
      >
        <div className="mob-nav-icon-wrap">
          {checkingSafety ? (
            <Loader2 size={18} className="spin-anim" color="var(--accent)" />
          ) : (
            <MapPin size={18} color={deviceCoords ? '#30D158' : 'var(--accent)'} />
          )}
          {deviceCoords && <span className="mob-nav-badge-dot" />}
        </div>
        <span className="mob-nav-label">Near Me</span>
      </button>

      <button
        type="button"
        className="mob-nav-btn mob-nav-btn-highlight"
        onClick={onReportHazard}
        title="Report Field Hazard to Authority Triage"
      >
        <div className="mob-nav-icon-wrap highlight-wrap">
          <AlertTriangle size={18} color="#FFFFFF" />
        </div>
        <span className="mob-nav-label highlight-label">Report</span>
      </button>

      <button
        type="button"
        className={`mob-nav-btn ${planningRoute ? 'active' : ''}`}
        onClick={onSafeRoute}
        disabled={planningRoute}
        title="Calculate Safe Evacuation Corridor to Nearest Camp"
      >
        <div className="mob-nav-icon-wrap">
          {planningRoute ? (
            <Loader2 size={18} className="spin-anim" color="var(--accent)" />
          ) : (
            <Navigation size={18} color="var(--accent)" />
          )}
        </div>
        <span className="mob-nav-label">Evac Route</span>
      </button>

      <button
        type="button"
        className="mob-nav-btn"
        onClick={onOpenHelplines}
        title="Emergency Helplines Directory"
      >
        <div className="mob-nav-icon-wrap">
          <PhoneCall size={18} color="#F59E0B" />
        </div>
        <span className="mob-nav-label">Helplines</span>
      </button>

      <button
        type="button"
        className="mob-nav-btn"
        onClick={onOpenMenu}
        title="Open Disaster Command Menu"
      >
        <div className="mob-nav-icon-wrap">
          <Menu size={18} color="var(--text-primary)" />
        </div>
        <span className="mob-nav-label">Menu</span>
      </button>
    </nav>
  );
}
