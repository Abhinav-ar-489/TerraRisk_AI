import { useState } from 'react';
import { X, User, Phone, Lock, MapPin, Shield, AlertCircle, Navigation, Sparkles } from 'lucide-react';
import axios from 'axios';

const KERALA_DISTRICTS = [
  'Wayanad',
  'Idukki',
  'Malappuram',
  'Kozhikode',
  'Palakkad',
  'Pathanamthitta',
  'Kottayam',
  'Ernakulam',
  'Thrissur',
  'Kannur',
  'Kasaragod',
  'Alappuzha',
  'Kollam',
  'Thiruvananthapuram'
];

export default function AuthModal({ isOpen, onClose, onAuthSuccess, triggerToast }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Login form state
  const [loginPhone, setLoginPhone] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [regName, setRegName] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('Citizen');
  const [regDistrict, setRegDistrict] = useState('Wayanad');
  const [regLat, setRegLat] = useState(11.5510);
  const [regLng, setRegLng] = useState(76.1280);
  const [locating, setLocating] = useState(false);

  if (!isOpen) return null;

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      triggerToast('Geolocation is not supported by your browser.', 'error');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setRegLat(parseFloat(position.coords.latitude.toFixed(4)));
        setRegLng(parseFloat(position.coords.longitude.toFixed(4)));
        setLocating(false);
        triggerToast('✓ Home GPS Coordinates Acquired', 'success');
      },
      () => {
        setLocating(false);
        triggerToast('Could not retrieve current location. Using default Kerala coordinates.', 'error');
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const validatePhone = (phone) => {
    const digits = phone.replace(/[\s\-]/g, '');
    let core = digits;
    if (digits.startsWith('+91')) core = digits.slice(3);
    else if (digits.startsWith('91') && digits.length === 12) core = digits.slice(2);
    else core = digits.replace(/^\+/, '');
    return /^[6-9]\d{9}$/.test(core);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    if (!loginPhone.trim()) {
      setError('Phone number is required.');
      return;
    }
    if (!validatePhone(loginPhone)) {
      setError('Enter a valid 10-digit Indian mobile number (starts with 6–9).');
      return;
    }
    if (!loginPassword) {
      setError('Password is required.');
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/auth/login', {
        phone: loginPhone.trim(),
        password: loginPassword
      });
      if (res.data.success) {
        onAuthSuccess(res.data.token, res.data.user);
        triggerToast(`Welcome back, ${res.data.user.name}!`, 'success');
        onClose();
      } else {
        setError(res.data.error || 'Authentication failed.');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid credentials or server unavailable.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    // Name
    const name = regName.trim();
    if (!name) { setError('Full name is required.'); return; }
    if (name.length < 2) { setError('Name must be at least 2 characters.'); return; }
    if (name.length > 60) { setError('Name must be under 60 characters.'); return; }
    if (!/^[A-Za-z\s\-.]+$/.test(name)) { setError('Name can only contain letters, spaces, hyphens, or dots.'); return; }

    // Phone
    if (!regPhone.trim()) { setError('Phone number is required.'); return; }
    if (!validatePhone(regPhone)) {
      setError('Enter a valid 10-digit Indian mobile number (starts with 6–9).');
      return;
    }

    // Password
    if (!regPassword) { setError('Password is required.'); return; }
    if (regPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (regPassword.length > 128) { setError('Password is too long (max 128 characters).'); return; }
    if (!/[A-Za-z]/.test(regPassword)) { setError('Password must contain at least one letter.'); return; }
    if (!/\d/.test(regPassword)) { setError('Password must contain at least one number.'); return; }

    setLoading(true);
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/auth/register', {
        name,
        phone: regPhone.trim(),
        password: regPassword,
        role: regRole,
        district: regDistrict,
        lat: regLat,
        lng: regLng
      });
      if (res.data.success) {
        onAuthSuccess(res.data.token, res.data.user);
        triggerToast(`Welcome to TerraRisk AI, ${res.data.user.name}!`, 'success');
        onClose();
      } else {
        setError(res.data.error || 'Registration failed.');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Registration error. Phone number may already be in use.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAdmin = () => {
    setTab('login');
    setLoginPhone('+919999900000');
    setLoginPassword('Admin@Terra2026!');
    setError('');
  };

  const fillDemoCitizen = () => {
    setTab('login');
    setLoginPhone('+919847012345');
    setLoginPassword('SecurePassword123!');
    setError('');
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="auth-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <div>
            <h2 className="auth-title">
              TERRARISK <span style={{ color: 'var(--accent)' }}>AUTH</span>
            </h2>
            <p className="auth-subtitle">Disaster Telemetry & Credibility Access</p>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="auth-tab-bar">
          <button
            className={`auth-tab-btn ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setError(''); }}
          >
            Sign In
          </button>
          <button
            className={`auth-tab-btn ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(''); }}
          >
            Register Profile
          </button>
        </div>

        {error && (
          <div className="auth-error-banner">
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}

        {tab === 'login' ? (
          <form onSubmit={handleLogin} className="auth-form">
            <div className="auth-field-group">
              <label className="auth-label"><Phone size={12} /> Phone Number</label>
              <input
                type="text"
                placeholder="+919876543210"
                value={loginPhone}
                onChange={(e) => setLoginPhone(e.target.value)}
                className="auth-input"
                required
              />
            </div>

            <div className="auth-field-group">
              <label className="auth-label"><Lock size={12} /> Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                className="auth-input"
                required
              />
            </div>

            <button type="submit" className="ios-button auth-submit-btn" disabled={loading}>
              {loading ? 'Authenticating Matrix...' : 'Sign In'}
            </button>

            {/* Quick Demo Logins */}
            <div className="auth-demo-section">
              <span className="auth-demo-label"><Sparkles size={12} color="var(--accent)" /> Quick Demo Presets:</span>
              <div className="auth-demo-buttons-grid">
                <button type="button" onClick={fillDemoAdmin} className="auth-demo-pill admin">
                  🛡️ Authority Admin
                </button>
                <button type="button" onClick={fillDemoCitizen} className="auth-demo-pill citizen">
                  👤 Citizen User
                </button>
              </div>
            </div>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="auth-form">
            <div className="auth-field-group">
              <label className="auth-label"><User size={12} /> Full Name</label>
              <input
                type="text"
                placeholder="e.g. Abhinav"
                value={regName}
                onChange={(e) => setRegName(e.target.value)}
                className="auth-input"
                required
              />
            </div>

            <div className="auth-field-row">
              <div className="auth-field-group" style={{ flex: 1 }}>
                <label className="auth-label"><Phone size={12} /> Phone Number</label>
                <input
                  type="text"
                  placeholder="+919847000111"
                  value={regPhone}
                  onChange={(e) => setRegPhone(e.target.value)}
                  className="auth-input"
                  required
                />
              </div>

              <div className="auth-field-group" style={{ flex: 1 }}>
                <label className="auth-label"><Lock size={12} /> Password</label>
                <input
                  type="password"
                  placeholder="Min 6 characters"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  className="auth-input"
                  required
                />
              </div>
            </div>

            <div className="auth-field-row">
              <div className="auth-field-group" style={{ flex: 1 }}>
                <label className="auth-label"><Shield size={12} /> Account Role</label>
                <select
                  value={regRole}
                  onChange={(e) => setRegRole(e.target.value)}
                  className="auth-input auth-select"
                >
                  <option value="Citizen">Citizen</option>
                  <option value="Volunteer">Volunteer (Field First Responder)</option>
                </select>
              </div>

              <div className="auth-field-group" style={{ flex: 1 }}>
                <label className="auth-label"><MapPin size={12} /> Home District</label>
                <select
                  value={regDistrict}
                  onChange={(e) => setRegDistrict(e.target.value)}
                  className="auth-input auth-select"
                >
                  {KERALA_DISTRICTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Coordinates / GPS capture */}
            <div className="auth-coords-box">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-secondary)' }}>
                  Home Coordinates: ({regLat.toFixed(3)}°N, {regLng.toFixed(3)}°E)
                </span>
                <button
                  type="button"
                  onClick={handleGetLocation}
                  className="auth-gps-btn"
                  disabled={locating}
                >
                  <Navigation size={12} /> {locating ? 'Detecting...' : 'Detect GPS'}
                </button>
              </div>
            </div>

            <button type="submit" className="ios-button auth-submit-btn" disabled={loading}>
              {loading ? 'Creating Account...' : 'Register Profile (50 Credibility)'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
