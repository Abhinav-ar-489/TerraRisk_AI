import { useState, useEffect } from 'react';
import { 
  X, User, Phone, Mail, Lock, Eye, EyeOff, ShieldCheck, 
  Shield, LogIn, UserPlus, ArrowRight, ArrowLeft,
  Check, AlertCircle, ShieldAlert, CheckCircle2, Circle,
  MapPin, Navigation, RefreshCw, KeyRound, Sparkles
} from 'lucide-react';
import api from '../services/api';

// Kerala 14 Districts centroids for reverse geocoding & manual selection
const KERALA_DISTRICTS = [
  { name: 'Wayanad', lat: 11.6854, lng: 76.1320 },
  { name: 'Idukki', lat: 9.9189, lng: 76.9444 },
  { name: 'Malappuram', lat: 11.0510, lng: 76.0711 },
  { name: 'Kozhikode', lat: 11.2588, lng: 75.7804 },
  { name: 'Palakkad', lat: 10.7867, lng: 76.6548 },
  { name: 'Thrissur', lat: 10.5276, lng: 76.2144 },
  { name: 'Ernakulam', lat: 9.9816, lng: 76.2999 },
  { name: 'Kottayam', lat: 9.5916, lng: 76.5222 },
  { name: 'Alappuzha', lat: 9.4981, lng: 76.3388 },
  { name: 'Pathanamthitta', lat: 9.2648, lng: 76.7870 },
  { name: 'Kollam', lat: 8.8932, lng: 76.6141 },
  { name: 'Thiruvananthapuram', lat: 8.5241, lng: 76.9366 },
  { name: 'Kannur', lat: 11.8745, lng: 75.3704 },
  { name: 'Kasaragod', lat: 12.5102, lng: 74.9852 }
];

function getClosestDistrict(lat, lng) {
  let closest = KERALA_DISTRICTS[0];
  let minDistance = Infinity;
  for (const d of KERALA_DISTRICTS) {
    const dLat = lat - d.lat;
    const dLng = lng - d.lng;
    const distSq = dLat * dLat + dLng * dLng;
    if (distSq < minDistance) {
      minDistance = distSq;
      closest = d;
    }
  }
  return closest.name;
}

export default function AuthModal({ isOpen, onClose, onAuthSuccess, triggerToast }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [step, setStep] = useState('form'); // 'form' | 'verify_email'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Login form state
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [regContactType, setRegContactType] = useState('email'); // 'email' | 'phone'
  const [regName, setRegName] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [showSecondaryContact, setShowSecondaryContact] = useState(false);
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('Citizen'); // 'Citizen' | 'Volunteer'
  const [regDistrict, setRegDistrict] = useState('Wayanad');
  const [regLat, setRegLat] = useState(null);
  const [regLng, setRegLng] = useState(null);
  const [regAccuracy, setRegAccuracy] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationSuccess, setLocationSuccess] = useState(false);

  // Verification step state
  const [otpCode, setOtpCode] = useState('');
  const [devOtp, setDevOtp] = useState('');
  const [resendTimer, setResendTimer] = useState(0);
  const [resendLoading, setResendLoading] = useState(false);
  const [showBackupCode, setShowBackupCode] = useState(false);

  // Countdown timer for OTP resend
  useEffect(() => {
    let interval = null;
    if (resendTimer > 0) {
      interval = setInterval(() => {
        setResendTimer((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [resendTimer]);

  if (!isOpen) return null;

  const normalizePhoneInput = (val) => {
    let cleaned = val.replace(/[^\d+]/g, '');
    if (cleaned.startsWith('+91')) cleaned = cleaned.slice(3);
    else if (cleaned.startsWith('+')) cleaned = cleaned.slice(1);
    return cleaned;
  };

  const validatePhone = (phone) => {
    const digits = phone.replace(/[\s-]/g, '');
    let core;
    if (digits.startsWith('+91')) core = digits.slice(3);
    else if (digits.startsWith('91') && digits.length === 12) core = digits.slice(2);
    else core = digits.replace(/^\+/, '');
    return /^[6-9]\d{9}$/.test(core);
  };

  const validateEmail = (email) => {
    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    return emailRegex.test(email.trim());
  };

  // Live password validation rules
  const hasMinLength = regPassword.length >= 8;
  const hasLetter = /[A-Za-z]/.test(regPassword);
  const hasNumber = /\d/.test(regPassword);
  const isPasswordValid = hasMinLength && hasLetter && hasNumber;

  // Auto-fetch location with GPS & reverse Kerala district detection
  const handleAutoFetchLocation = () => {
    if (!navigator.geolocation) {
      triggerToast('Geolocation is not supported by your browser.', 'warning');
      return;
    }
    setIsLocating(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = parseFloat(pos.coords.latitude.toFixed(5));
        const lng = parseFloat(pos.coords.longitude.toFixed(5));
        const accuracy = Math.round(pos.coords.accuracy);
        setRegLat(lat);
        setRegLng(lng);
        setRegAccuracy(accuracy);

        // Detect closest Kerala district
        const detectedDistrict = getClosestDistrict(lat, lng);
        setRegDistrict(detectedDistrict);
        setLocationSuccess(true);
        setIsLocating(false);
        triggerToast(`📍 Location detected: ${detectedDistrict} (${lat}°, ${lng}°)`, 'success');
      },
      (err) => {
        setIsLocating(false);
        console.warn('Geolocation error:', err.message);
        setError('Location auto-fetch was denied. Please select your district from the dropdown below.');
        triggerToast('Could not fetch GPS. Please pick district manually.', 'info');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  // Login handler
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    const ident = loginIdentifier.trim();
    if (!ident) {
      setError('Mobile phone number or email address is required.');
      return;
    }
    if (!loginPassword) {
      setError('Password is required.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/api/auth/login', {
        identifier: ident,
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
      if (err.response?.data?.requires_verification) {
        // Redirect to email verification step
        setRegEmail(err.response.data.email || ident);
        setDevOtp(err.response.data.dev_otp || '');
        setTab('register');
        setStep('verify_email');
        setResendTimer(30);
        setError('Your email is not verified yet. A 6-digit code has been sent to your email.');
      } else if (!err.response) {
        setError('Unable to reach backend server. Please check connection status.');
      } else {
        setError(err.response?.data?.error || 'Invalid credentials or login failed.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Register form submission
  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Name validation
    const name = regName.trim();
    if (!name || name.length < 2) { setError('Name must be at least 2 characters.'); return; }
    if (name.length > 60) { setError('Name must be under 60 characters.'); return; }
    if (!/^[A-Za-z0-9\s._'’-]+$/.test(name)) { setError('Name contains invalid characters.'); return; }

    // Contact validation: Either Phone or Email (based on user selection)
    let cleanPhone = null;
    let cleanEmail = null;

    if (regContactType === 'phone') {
      const p = normalizePhoneInput(regPhone);
      if (!p || !validatePhone(p)) {
        setError('Please enter a valid 10-digit Indian mobile number (starts with 6–9).');
        return;
      }
      cleanPhone = '+91' + p;
      if (regEmail.trim()) {
        if (!validateEmail(regEmail.trim())) {
          setError('Optional email format is invalid.');
          return;
        }
        cleanEmail = regEmail.trim().toLowerCase();
      }
    } else {
      // regContactType === 'email'
      if (!regEmail.trim() || !validateEmail(regEmail.trim())) {
        setError('Please enter a valid email address for verification.');
        return;
      }
      cleanEmail = regEmail.trim().toLowerCase();
      if (regPhone.trim()) {
        const p = normalizePhoneInput(regPhone);
        if (!validatePhone(p)) {
          setError('Optional mobile number must be 10 digits.');
          return;
        }
        cleanPhone = '+91' + p;
      }
    }

    // Password validation
    if (!regPassword || !isPasswordValid) {
      setError('Please ensure password meets all criteria (8+ chars, 1 letter, 1 number).');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        name,
        password: regPassword,
        role: regRole,
        district: regDistrict,
        lat: regLat,
        lng: regLng
      };
      if (cleanPhone) payload.phone = cleanPhone;
      if (cleanEmail) payload.email = cleanEmail;

      const res = await api.post('/api/auth/register', payload);

      if (res.data.success) {
        if (res.data.step === 'verify_email') {
          // Advance to email verification page
          setDevOtp(res.data.dev_otp || '');
          setStep('verify_email');
          setResendTimer(30);
          triggerToast(`Verification code sent to ${cleanEmail}`, 'info');
        } else {
          // Phone-only registration complete
          onAuthSuccess(res.data.token, res.data.user);
          triggerToast(`✓ Welcome to TerraRisk AI, ${res.data.user.name}!`, 'success');
          onClose();
        }
      } else {
        setError(res.data.error || 'Registration failed.');
      }
    } catch (err) {
      if (!err.response) {
        setError('Unable to reach backend server. Please ensure backend is running.');
      } else {
        setError(err.response?.data?.error || 'Registration failed. Phone or email may already be registered.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Email OTP verification submission
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError('');
    const code = otpCode.trim();
    if (!code || code.length !== 6 || !/^\d{6}$/.test(code)) {
      setError('Please enter the 6-digit numeric verification code.');
      return;
    }

    setLoading(true);
    try {
      const res = await api.post('/api/auth/verify-email', {
        email: regEmail.trim().toLowerCase(),
        code
      });

      if (res.data.success) {
        onAuthSuccess(res.data.token, res.data.user);
        triggerToast(`✓ Verified! Welcome to TerraRisk AI, ${res.data.user.name}!`, 'success');
        onClose();
      } else {
        setError(res.data.error || 'Verification failed.');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid or expired verification code.');
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP handler
  const handleResendCode = async () => {
    if (resendTimer > 0 || resendLoading) return;
    setResendLoading(true);
    setError('');
    try {
      const res = await api.post('/api/auth/resend-code', {
        email: regEmail.trim().toLowerCase()
      });
      if (res.data.success) {
        setDevOtp(res.data.dev_otp || '');
        setResendTimer(30);
        triggerToast(`New verification code sent to ${regEmail}`, 'success');
      } else {
        setError(res.data.error || 'Could not resend code.');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to resend code.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div 
        className="auth-modal-content ios-glass" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="mobile-bottom-sheet-handle" />
        {/* Modal Header */}
        <div className="auth-modal-header">
          <div className="auth-header-brand">
            <div className="auth-brand-badge">
              <ShieldAlert size={18} color="#0EA5E9" />
            </div>
            <div>
              <h2 className="auth-title">
                TerraRisk <span className="auth-title-accent">Auth</span>
              </h2>
              <p className="auth-subtitle">Disaster Early Warning & Command Portal</p>
            </div>
          </div>
          <button 
            type="button" 
            className="auth-close-btn" 
            onClick={onClose}
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Switcher (Sign In vs Register) */}
        <div className="auth-tab-bar">
          <button
            type="button"
            className={`auth-tab-btn ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setStep('form'); setError(''); }}
          >
            <LogIn size={13} />
            <span>Sign In</span>
          </button>
          <button
            type="button"
            className={`auth-tab-btn ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(''); }}
          >
            <UserPlus size={13} />
            <span>Register Profile</span>
          </button>
        </div>

        {/* Error Alert Box */}
        {error && (
          <div className="auth-error-banner">
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 1: LOGIN (Dual Phone or Email Identifier) */}
        {/* ==================================================================== */}
        {tab === 'login' && (
          <form onSubmit={handleLogin} className="auth-form">
            {/* Phone or Email Identifier */}
            <div className="auth-field-group">
              <label className="auth-label">
                <User size={12} className="auth-label-icon" /> Mobile Phone Number or Email ID
              </label>
              <div className="auth-input-wrapper">
                <input
                  type="text"
                  placeholder="e.g. 9847012345 or citizen@terrarisk.org"
                  value={loginIdentifier}
                  onChange={(e) => setLoginIdentifier(e.target.value)}
                  className="auth-input"
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="auth-field-group">
              <label className="auth-label">
                <Lock size={12} className="auth-label-icon" /> Password
              </label>
              <div className="auth-input-wrapper">
                <Lock size={15} className="auth-field-prefix-icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="auth-input"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Submit Action */}
            <button 
              type="submit" 
              className="auth-submit-btn" 
              disabled={loading}
            >
              {loading ? (
                <span className="auth-btn-loading">
                  <span className="auth-spinner" /> Authenticating...
                </span>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight size={15} />
                </>
              )}
            </button>

            {/* Quick Fill Test Accounts */}
            <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
              <span style={{ fontSize: '11px', fontWeight: '550', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '8px' }}>
                Quick Test Accounts (Click to Auto-Fill)
              </span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
                <button
                  type="button"
                  onClick={() => {
                    setLoginIdentifier('citizen@terrarisk.org');
                    setLoginPassword('SecurePassword123!');
                  }}
                  className="auth-quick-fill-btn"
                >
                  👤 Citizen
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLoginIdentifier('volunteer@terrarisk.org');
                    setLoginPassword('Volunteer@2026!');
                  }}
                  className="auth-quick-fill-btn"
                >
                  ⛑️ Volunteer
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLoginIdentifier('admin@terrarisk.gov.in');
                    setLoginPassword('A12345678');
                  }}
                  className="auth-quick-fill-btn admin"
                >
                  🛡️ Admin
                </button>
              </div>
            </div>
          </form>
        )}

        {/* ==================================================================== */}
        {/* TAB 2: REGISTER (Step 1: Details with Either Email OR Phone) */}
        {/* ==================================================================== */}
        {tab === 'register' && step === 'form' && (
          <form onSubmit={handleRegisterSubmit} className="auth-form">
            {/* Full Name */}
            <div className="auth-field-group">
              <label className="auth-label">
                <User size={12} className="auth-label-icon" /> Full Name
              </label>
              <div className="auth-input-wrapper">
                <User size={15} className="auth-field-prefix-icon" />
                <input
                  type="text"
                  placeholder="e.g. Abhinav R"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  className="auth-input"
                  autoComplete="name"
                  required
                />
              </div>
            </div>

            {/* Registration Contact Method Choice: Email OR Phone */}
            <div className="auth-field-group">
              <label className="auth-label">
                Register Using (Choose Either Email or Phone)
              </label>
              <div className="auth-contact-mode-bar">
                <button
                  type="button"
                  className={`auth-contact-mode-btn ${regContactType === 'email' ? 'active' : ''}`}
                  onClick={() => { setRegContactType('email'); setError(''); }}
                >
                  <Mail size={13} />
                  <span>Email ID</span>
                </button>
                <button
                  type="button"
                  className={`auth-contact-mode-btn ${regContactType === 'phone' ? 'active' : ''}`}
                  onClick={() => { setRegContactType('phone'); setError(''); }}
                >
                  <Phone size={13} />
                  <span>Phone Number</span>
                </button>
              </div>
            </div>

            {/* If Email Mode Selected */}
            {regContactType === 'email' && (
              <div className="auth-field-group">
                <label className="auth-label">
                  <Mail size={12} className="auth-label-icon" /> Email Address (for 6-digit OTP)
                </label>
                <div className="auth-input-wrapper">
                  <Mail size={15} className="auth-field-prefix-icon" />
                  <input
                    type="email"
                    placeholder="e.g. citizen@example.com"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    className="auth-input"
                    autoComplete="email"
                    required
                  />
                </div>
                {!showSecondaryContact ? (
                  <button
                    type="button"
                    onClick={() => setShowSecondaryContact(true)}
                    className="auth-optional-link"
                  >
                    + Add Mobile Number (Optional)
                  </button>
                ) : (
                  <div style={{ marginTop: '6px' }}>
                    <div className="auth-input-wrapper">
                      <span className="auth-country-flag">+91</span>
                      <input
                        type="tel"
                        placeholder="Mobile Number (Optional)"
                        value={regPhone}
                        onChange={(e) => setRegPhone(normalizePhoneInput(e.target.value))}
                        className="auth-input"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* If Phone Mode Selected */}
            {regContactType === 'phone' && (
              <div className="auth-field-group">
                <label className="auth-label">
                  <Phone size={12} className="auth-label-icon" /> Indian Mobile Number (+91)
                </label>
                <div className="auth-input-wrapper">
                  <span className="auth-country-flag">+91</span>
                  <input
                    type="tel"
                    placeholder="9847012345"
                    value={regPhone}
                    onChange={(e) => setRegPhone(normalizePhoneInput(e.target.value))}
                    className="auth-input"
                    autoComplete="tel"
                    required
                  />
                </div>
                {!showSecondaryContact ? (
                  <button
                    type="button"
                    onClick={() => setShowSecondaryContact(true)}
                    className="auth-optional-link"
                  >
                    + Add Email Address (Optional)
                  </button>
                ) : (
                  <div style={{ marginTop: '6px' }}>
                    <div className="auth-input-wrapper">
                      <Mail size={15} className="auth-field-prefix-icon" />
                      <input
                        type="email"
                        placeholder="Email Address (Optional)"
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        className="auth-input"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Location Auto-Fetch Widget */}
            <div className="auth-field-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label className="auth-label" style={{ marginBottom: 0 }}>
                  <MapPin size={12} className="auth-label-icon" /> Location & Kerala District
                </label>
                <button
                  type="button"
                  onClick={handleAutoFetchLocation}
                  disabled={isLocating}
                  className="auth-location-fetch-btn"
                >
                  {isLocating ? (
                    <>
                      <span className="auth-spinner mini" /> Detecting GPS...
                    </>
                  ) : (
                    <>
                      <Navigation size={11} /> Auto-Fetch Location
                    </>
                  )}
                </button>
              </div>

              {locationSuccess && (
                <div className="auth-location-badge">
                  <CheckCircle2 size={13} color="#10B981" />
                  <span>
                    Detected: <strong>{regDistrict}</strong> ({regLat}° N, {regLng}° E) • &plusmn;{regAccuracy}m
                  </span>
                </div>
              )}

              {/* District Dropdown Selector */}
              <div className="auth-input-wrapper" style={{ marginTop: '6px' }}>
                <MapPin size={15} className="auth-field-prefix-icon" />
                <select
                  value={regDistrict}
                  onChange={(e) => setRegDistrict(e.target.value)}
                  className="auth-input auth-select"
                >
                  {KERALA_DISTRICTS.map((d) => (
                    <option key={d.name} value={d.name}>
                      {d.name} District (Kerala)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Password */}
            <div className="auth-field-group">
              <label className="auth-label">
                <Lock size={12} className="auth-label-icon" /> Password
              </label>
              <div className="auth-input-wrapper">
                <Lock size={15} className="auth-field-prefix-icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a strong password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  className="auth-input"
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>

              {/* Password criteria pills */}
              {regPassword.length > 0 && (
                <div className="auth-pwd-criteria-row">
                  <span className={`auth-pwd-pill ${hasMinLength ? 'met' : ''}`}>
                    {hasMinLength ? <CheckCircle2 size={11} /> : <Circle size={11} />}
                    8+ Chars
                  </span>
                  <span className={`auth-pwd-pill ${hasLetter ? 'met' : ''}`}>
                    {hasLetter ? <CheckCircle2 size={11} /> : <Circle size={11} />}
                    1 Letter
                  </span>
                  <span className={`auth-pwd-pill ${hasNumber ? 'met' : ''}`}>
                    {hasNumber ? <CheckCircle2 size={11} /> : <Circle size={11} />}
                    1 Number
                  </span>
                </div>
              )}
            </div>

            {/* Account Role Selector Cards */}
            <div className="auth-field-group">
              <label className="auth-label">
                <Shield size={12} className="auth-label-icon" /> Select Account Role
              </label>
              <div className="auth-role-grid">
                <div 
                  className={`auth-role-card ${regRole === 'Citizen' ? 'selected' : ''}`}
                  onClick={() => setRegRole('Citizen')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="auth-role-title-row">
                    <span className="auth-role-badge citizen">👤 Citizen</span>
                    {regRole === 'Citizen' && <span className="auth-role-check"><Check size={12} /></span>}
                  </div>
                </div>

                <div 
                  className={`auth-role-card ${regRole === 'Volunteer' ? 'selected' : ''}`}
                  onClick={() => setRegRole('Volunteer')}
                  role="button"
                  tabIndex={0}
                >
                  <div className="auth-role-title-row">
                    <span className="auth-role-badge volunteer">⛑️ Volunteer</span>
                    {regRole === 'Volunteer' && <span className="auth-role-check"><Check size={12} /></span>}
                  </div>
                </div>
              </div>
            </div>

            {/* Dynamic Submit Button depending on email vs phone */}
            <button 
              type="submit" 
              className="auth-submit-btn" 
              disabled={loading}
            >
              {loading ? (
                <span className="auth-btn-loading">
                  <span className="auth-spinner" /> Processing...
                </span>
              ) : regContactType === 'email' ? (
                <>
                  <span>Continue to Email Verification</span>
                  <ArrowRight size={15} />
                </>
              ) : (
                <>
                  <span>Register Profile</span>
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>
        )}

        {/* ==================================================================== */}
        {/* TAB 2: REGISTER (Step 2: Email Verification OTP Page) */}
        {/* ==================================================================== */}
        {tab === 'register' && step === 'verify_email' && (
          <form onSubmit={handleVerifyOtp} className="auth-form auth-verify-step-form">
            <div className="auth-verify-step-header">
              <div className="auth-verify-mail-badge">
                <Mail size={24} color="#0284C7" />
              </div>
              <h3 className="auth-verify-step-title">Verify Your Email Address</h3>
              <p className="auth-verify-step-sub">
                We've dispatched a 6-digit security code to:
                <br />
                <strong className="auth-verify-target-email">{regEmail}</strong>
              </p>
              <button
                type="button"
                onClick={() => { setStep('form'); setError(''); }}
                className="auth-change-email-btn"
              >
                <ArrowLeft size={12} /> Edit Email Address
              </button>
            </div>

            {/* OTP Input Field */}
            <div className="auth-field-group">
              <label className="auth-label" style={{ textAlign: 'center', display: 'block' }}>
                <KeyRound size={12} className="auth-label-icon" /> Enter 6-Digit Verification Code
              </label>
              <div className="auth-otp-input-wrapper">
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  autoComplete="one-time-code"
                  maxLength={6}
                  placeholder="••••••"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  className="auth-otp-input"
                  autoFocus
                  required
                />
              </div>
              {devOtp && (
                <div style={{ textAlign: 'center', marginTop: '8px' }}>
                  {!showBackupCode ? (
                    <button
                      type="button"
                      onClick={() => setShowBackupCode(true)}
                      className="auth-backup-otp-toggle"
                    >
                      <Sparkles size={11} color="#F59E0B" />
                      <span>Slow network? Reveal demo backup code</span>
                    </button>
                  ) : (
                    <div className="auth-dev-otp-hint">
                      <Sparkles size={12} color="#F59E0B" />
                      <span>Backup Code: <strong>{devOtp}</strong></span>
                      <button
                        type="button"
                        onClick={() => setOtpCode(devOtp)}
                        className="auth-otp-fill-btn"
                      >
                        Auto-Fill
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Verify Button */}
            <button 
              type="submit" 
              className="auth-submit-btn" 
              disabled={loading || otpCode.length !== 6}
            >
              {loading ? (
                <span className="auth-btn-loading">
                  <span className="auth-spinner" /> Verifying Code...
                </span>
              ) : (
                <>
                  <ShieldCheck size={16} />
                  <span>Verify & Complete Registration</span>
                </>
              )}
            </button>

            {/* Resend Code Section */}
            <div className="auth-resend-row">
              {resendTimer > 0 ? (
                <span className="auth-resend-timer-text">
                  Resend code in <strong>{resendTimer}s</strong>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={handleResendCode}
                  disabled={resendLoading}
                  className="auth-resend-btn"
                >
                  <RefreshCw size={12} className={resendLoading ? 'spin' : ''} />
                  <span>Didn't receive code? Resend Code</span>
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
