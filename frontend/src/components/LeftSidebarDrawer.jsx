import { 
  X, Compass, ShieldAlert, HeartHandshake, UserX, 
  Shield, ShieldCheck, Sliders, Navigation, PhoneCall, LogOut, 
  User, Sun, Moon, CheckCircle, Flame
} from 'lucide-react';

export default function LeftSidebarDrawer({
  isOpen,
  onClose,
  onOpenSafeRoute,
  onOpenReportHazard,
  onOpenMissingPersons,
  onOpenAuthoritySuite,
  onOpenSettings,
  onOpenHelplines,
  onCheckMyArea,
  checkingSafety,
  user,
  onOpenAuth,
  onLogout,
  theme,
  setTheme,
  planningRoute,
  pinDropMode
}) {
  if (!isOpen) return null;

  const isVerified = user?.is_verified || user?.role === 'Authority_Admin';

  const handleAction = (callback) => {
    onClose();
    if (callback) callback();
  };

  return (
    <div className="sidebar-backdrop" onClick={onClose}>
      <aside 
        className="sidebar-drawer ios-glass" 
        onClick={(e) => e.stopPropagation()}
        aria-label="Navigation Sidebar"
      >
        {/* Drawer Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand-block">
            <div className="sidebar-brand-title-row">
              <span className="brand-pulse-dot" />
              <span className="sidebar-brand-title">TERRARISK <span className="brand-accent">AI</span></span>
            </div>
            <span className="sidebar-brand-sub">KERALA DISASTER COMMAND</span>
          </div>
          <button className="sidebar-close-btn" onClick={onClose} title="Close Menu (Esc)">
            <X size={18} />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="sidebar-content-scroll">
          {/* Group 1: Emergency Operations */}
          <div className="sidebar-section-title">
            <Flame size={12} color="#EF4444" />
            <span>CRISIS OPERATIONS</span>
          </div>
          <div className="sidebar-nav-group">
            <button 
              className="sidebar-nav-item item-route"
              onClick={() => handleAction(onOpenSafeRoute)}
              disabled={planningRoute}
            >
              <div className="sidebar-item-icon route-icon">
                <Compass size={16} className={planningRoute ? 'spinning' : ''} />
              </div>
              <div className="sidebar-item-text">
                <span className="item-label">{planningRoute ? 'Routing Navigation...' : 'Safe Evacuation Route'}</span>
                <span className="item-desc">Hazard-Free Path to Nearest Camp</span>
              </div>
            </button>

            <button 
              className={`sidebar-nav-item item-report ${pinDropMode ? 'active' : ''}`}
              onClick={() => handleAction(onOpenReportHazard)}
            >
              <div className="sidebar-item-icon report-icon">
                <ShieldAlert size={16} />
              </div>
              <div className="sidebar-item-text">
                <span className="item-label">{pinDropMode ? 'Map Pin-Drop Active...' : 'Report Geological Hazard'}</span>
                <span className="item-desc">Computer Vision Photo Analysis</span>
              </div>
            </button>
          </div>

          {/* Group 2: Community & Relief */}
          <div className="sidebar-section-title">
            <HeartHandshake size={12} color="#38BDF8" />
            <span>COMMUNITY & RELIEF</span>
          </div>
          <div className="sidebar-nav-group">
            <button 
              className="sidebar-nav-item"
              onClick={() => handleAction(onOpenMissingPersons)}
            >
              <div className="sidebar-item-icon missing-icon">
                <UserX size={16} />
              </div>
              <div className="sidebar-item-text">
                <span className="item-label">Missing Persons Registry</span>
                <span className="item-desc">Community Search & Evacuee Matching</span>
              </div>
            </button>

            <button 
              className="sidebar-nav-item"
              onClick={() => handleAction(onOpenHelplines)}
            >
              <div className="sidebar-item-icon helpline-icon">
                <PhoneCall size={16} />
              </div>
              <div className="sidebar-item-text">
                <span className="item-label">24/7 Disaster Helplines</span>
                <span className="item-desc">112, 1077 (District), 1070 (State)</span>
              </div>
            </button>
          </div>

          {/* Group 3: Command Suite (Strictly restricted to Authority Officers) */}
          {user && user.role === 'Authority_Admin' && (
            <>
              <div className="sidebar-section-title">
                <Shield size={12} color="#3B82F6" />
                <span>KSDMA COMMAND & TRIAGE</span>
              </div>
              <div className="sidebar-nav-group">
                <button 
                  className="sidebar-nav-item item-authority"
                  onClick={() => handleAction(onOpenAuthoritySuite)}
                >
                  <div className="sidebar-item-icon authority-icon">
                    <Shield size={16} />
                  </div>
                  <div className="sidebar-item-text">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className="item-label">Command Center Suite</span>
                      <span className="ksdma-tag" style={{ fontSize: '9px', padding: '1px 6px' }}>OFFICER / SEOC</span>
                    </div>
                    <span className="item-desc">Camp Manager, CV Triage, SitRep PDF</span>
                  </div>
                </button>
              </div>
            </>
          )}

          {/* Group 4: GIS Cartography & Settings */}
          <div className="sidebar-section-title">
            <Sliders size={12} color="#38BDF8" />
            <span>GIS CARTOGRAPHY & SETTINGS</span>
          </div>
          <div className="sidebar-nav-group">
            <button 
              className="sidebar-nav-item"
              onClick={() => handleAction(onOpenSettings)}
            >
              <div className="sidebar-item-icon settings-icon">
                <Sliders size={16} />
              </div>
              <div className="sidebar-item-text">
                <span className="item-label">GIS Layers & Cartography</span>
                <span className="item-desc">Radar, SRTM Hillshade, Slope Mesh</span>
              </div>
            </button>

            {user && (
              <button 
                className="sidebar-nav-item"
                onClick={() => handleAction(onCheckMyArea)}
                disabled={checkingSafety}
              >
                <div className="sidebar-item-icon check-icon">
                  <Navigation size={16} />
                </div>
                <div className="sidebar-item-text">
                  <span className="item-label">{checkingSafety ? 'Evaluating Location...' : 'Check Location Safety'}</span>
                  <span className="item-desc">Live Hazard & Shelter Status</span>
                </div>
              </button>
            )}
          </div>
        </div>

        {/* Drawer Footer: User Profile & Session */}
        <div className="sidebar-footer">
          {user ? (
            <div className="sidebar-user-card">
              <div className="sidebar-user-avatar">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="sidebar-user-info">
                <div className="sidebar-user-name-row">
                  <span className="sidebar-user-name">{user.name}</span>
                  <span className={`user-role-tag ${user.role === 'Authority_Admin' ? 'admin' : 'citizen'}`}>
                    {user.role === 'Authority_Admin' ? 'ADMIN' : 'CITIZEN'}
                  </span>
                </div>
                <span className="sidebar-credibility-text" style={{ color: isVerified ? '#30D158' : '#94A3B8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {isVerified ? (
                    <><ShieldCheck size={11} color="#30D158" /> Verified Account</>
                  ) : (
                    <><CheckCircle size={11} color="#94A3B8" /> Active Citizen</>
                  )}
                </span>
              </div>
              <button 
                className="sidebar-logout-btn"
                onClick={() => handleAction(onLogout)}
                title="Sign Out"
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <button 
              className="sidebar-signin-btn"
              onClick={() => handleAction(onOpenAuth)}
            >
              <User size={16} />
              <span>Sign In / Register</span>
            </button>
          )}

          <div className="sidebar-theme-row">
            <span className="sidebar-theme-label">Interface Mode</span>
            <button 
              className="sidebar-theme-switch-btn"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              {theme === 'light' ? (
                <>
                  <Moon size={14} color="#38BDF8" />
                  <span>Dark Glass</span>
                </>
              ) : (
                <>
                  <Sun size={14} color="#F59E0B" />
                  <span>Light Canvas</span>
                </>
              )}
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
