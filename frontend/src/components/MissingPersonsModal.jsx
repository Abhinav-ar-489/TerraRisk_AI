import { useState, useEffect, useCallback } from 'react';
import { X, Search, AlertCircle, Plus, UserX, Phone, MapPin, HeartPulse, Home } from 'lucide-react';
import api from '../services/api';

export default function MissingPersonsModal({
  isOpen,
  onClose,
  user,
  token,
  shelters = [],
  triggerToast
}) {
  const [activeTab, setActiveTab] = useState('board'); // 'board' | 'report'
  const [persons, setPersons] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Report Form State
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('Male');
  const [lastKnownLocation, setLastKnownLocation] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [medicalNeeds, setMedicalNeeds] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Status update modal / dropdown
  const isAuthorityOrVolunteer = user?.role === 'Authority_Admin' || user?.role === 'Volunteer';

  const fetchMissingPersons = useCallback(async () => {
    setLoading(true);
    try {
      let url = '/api/missing-persons';
      const params = [];
      if (statusFilter !== 'all') params.push(`status=${statusFilter}`);
      if (searchQuery) params.push(`query=${encodeURIComponent(searchQuery)}`);
      if (params.length > 0) url += `?${params.join('&')}`;

      const res = await api.get(url);
      if (res.data.success) {
        setPersons(res.data.missing_persons);
      }
    } catch {
      console.log("Missing persons fetch gap.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery]);

  useEffect(() => {
    let ignore = false;
    if (isOpen) {
      const load = async () => {
        try {
          let url = '/api/missing-persons';
          const params = [];
          if (statusFilter !== 'all') params.push(`status=${statusFilter}`);
          if (searchQuery) params.push(`query=${encodeURIComponent(searchQuery)}`);
          if (params.length > 0) url += `?${params.join('&')}`;

          const res = await api.get(url);
          if (!ignore && res.data.success) {
            setPersons(res.data.missing_persons);
          }
        } catch {
          console.log("Missing persons fetch gap.");
        }
      };
      load();
    }
    return () => { ignore = true; };
  }, [isOpen, statusFilter, searchQuery]);

  if (!isOpen) return null;

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchMissingPersons();
  };

  const handleReportSubmit = async (e) => {
    e.preventDefault();
    if (!name || !lastKnownLocation) {
      triggerToast("Name and last known location are mandatory.", "error");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.post('/api/missing-persons/report', {
        name,
        age: age ? parseInt(age, 10) : null,
        gender,
        last_known_location: lastKnownLocation,
        contact_phone: contactPhone,
        medical_needs: medicalNeeds
      });

      if (res.data.success) {
        triggerToast(`✓ Missing person report for '${name}' registered in SOS Board.`, "success");
        setName('');
        setAge('');
        setLastKnownLocation('');
        setContactPhone('');
        setMedicalNeeds('');
        setActiveTab('board');
        fetchMissingPersons();
      } else {
        triggerToast(res.data.error || "Failed to submit report.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Error connecting to service.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateStatus = async (personId, newStatus, shelterId = null) => {
    if (!token && !localStorage.getItem('terrarisk_token')) return;
    try {
      const res = await api.post(`/api/missing-persons/${personId}/update-status`, {
        status: newStatus,
        located_at_shelter_id: shelterId
      });

      if (res.data.success) {
        triggerToast(`✓ Status updated to '${newStatus.replace('_', ' ').toUpperCase()}'`, "success");
        fetchMissingPersons();
      }
    } catch {
      triggerToast("Failed to update status.", "error");
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 12000 }}>
      <div className="missing-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="auth-header-icon" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}>
              <UserX size={22} />
            </div>
            <div>
              <h2 className="auth-title">Missing Persons & Rescue Registry</h2>
              <span className="auth-subtitle">Community Disaster SOS Board & Camp Evacuee Matching</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="family-tabs">
          <button
            className={`family-tab-btn ${activeTab === 'board' ? 'active' : ''}`}
            onClick={() => setActiveTab('board')}
          >
            <Search size={16} />
            <span>Search & Rescue Registry ({persons.length})</span>
          </button>
          <button
            className={`family-tab-btn ${activeTab === 'report' ? 'active' : ''}`}
            onClick={() => setActiveTab('report')}
          >
            <Plus size={16} />
            <span>Report Missing Person</span>
          </button>
        </div>

        {/* Tab 1: Board */}
        {activeTab === 'board' && (
          <div className="missing-tab-body">
            {/* Filter Bar */}
            <div className="missing-filter-bar">
              <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '8px', flex: 1 }}>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="Search by name or sector..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button type="submit" className="btn-secondary" style={{ padding: '8px 16px' }}>
                  Search
                </button>
              </form>

              <select
                className="auth-input"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{ width: '180px' }}
              >
                <option value="all">All Statuses</option>
                <option value="missing">Missing</option>
                <option value="search_in_progress">Search in Progress</option>
                <option value="located_safe">Located Safe</option>
                <option value="hospitalized">Hospitalized</option>
              </select>
            </div>

            {/* List */}
            {loading ? (
              <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
                Syncing missing persons registry...
              </div>
            ) : persons.length === 0 ? (
              <div className="empty-contacts-state">
                <AlertCircle size={32} color="var(--text-tertiary)" />
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  No missing persons registered under current filter.
                </p>
              </div>
            ) : (
              <div className="missing-cards-grid">
                {persons.map(p => {
                  const isSafe = p.status === 'located_safe';
                  const statusLabel = p.status ? p.status.replace(/_/g, ' ').toUpperCase() : 'MISSING';

                  return (
                    <div key={p.id} className={`missing-person-card ${isSafe ? 'safe' : ''}`}>
                      <div className="missing-card-top">
                        <div>
                          <div style={{ fontWeight: '600', fontSize: '14.5px', color: 'var(--text-primary)' }}>
                            {p.name} {p.age ? `(${p.age} yrs, ${p.gender || 'M'})` : ''}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                            Reported: {new Date(p.created_at).toLocaleDateString()}
                          </div>
                        </div>

                        <span className={`status-badge-pill ${p.status}`}>
                          {statusLabel}
                        </span>
                      </div>

                      <div className="missing-card-details">
                        <div className="detail-row">
                          <MapPin size={13} color="#EF4444" />
                          <span>Last Known: <strong>{p.last_known_location}</strong></span>
                        </div>

                        {p.contact_phone && (
                          <div className="detail-row">
                            <Phone size={13} color="#38BDF8" />
                            <span>Contact: {p.contact_phone}</span>
                          </div>
                        )}

                        {p.medical_needs && (
                          <div className="detail-row">
                            <HeartPulse size={13} color="#EC4899" />
                            <span>Medical: <strong style={{ color: '#FF453A' }}>{p.medical_needs}</strong></span>
                          </div>
                        )}

                        {isSafe && p.located_shelter_name && (
                          <div className="detail-row" style={{ color: '#30D158' }}>
                            <Home size={13} color="#30D158" />
                            <span>Safely Admitted to: <strong>{p.located_shelter_name}</strong></span>
                          </div>
                        )}
                      </div>

                      {/* Authority Actions to match with Camp */}
                      {isAuthorityOrVolunteer && !isSafe && (
                        <div className="authority-match-strip">
                          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Mark as Located at:</span>
                          <select
                            className="auth-input match-select"
                            onChange={(e) => {
                              if (e.target.value) {
                                handleUpdateStatus(p.id, 'located_safe', parseInt(e.target.value, 10));
                              }
                            }}
                            defaultValue=""
                          >
                            <option value="" disabled>Select Relief Shelter Camp...</option>
                            {shelters.map(s => (
                              <option key={s.id} value={s.id}>{s.name} ({s.district})</option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Report Missing Person */}
        {activeTab === 'report' && (
          <form onSubmit={handleReportSubmit} className="missing-tab-body">
            <div className="form-section-label">Individual Details</div>
            <div className="form-grid-3">
              <div className="auth-field">
                <label className="auth-label">Full Name *</label>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Anand Kumar"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="auth-field">
                <label className="auth-label">Age</label>
                <input
                  type="number"
                  className="auth-input"
                  placeholder="e.g. 34"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  min="0"
                  max="120"
                />
              </div>
              <div className="auth-field">
                <label className="auth-label">Gender</label>
                <select
                  className="auth-input"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="form-grid-2" style={{ marginTop: '10px' }}>
              <div className="auth-field">
                <label className="auth-label">Last Known Sector / Address *</label>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Chooralmala Bridge Section 2"
                  value={lastKnownLocation}
                  onChange={(e) => setLastKnownLocation(e.target.value)}
                  required
                />
              </div>
              <div className="auth-field">
                <label className="auth-label">Emergency Phone (Family / Reporter)</label>
                <input
                  type="tel"
                  className="auth-input"
                  placeholder="+91..."
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                />
              </div>
            </div>

            <div className="auth-field" style={{ marginTop: '10px' }}>
              <label className="auth-label">Medical Needs / Distinctive Marks (Critical)</label>
              <textarea
                className="auth-input"
                rows={2}
                placeholder="e.g. Diabetic insulin dependency, red shirt, mobility assistance needed..."
                value={medicalNeeds}
                onChange={(e) => setMedicalNeeds(e.target.value)}
              />
            </div>

            <div className="camp-modal-footer" style={{ marginTop: '16px' }}>
              <button type="button" className="btn-secondary" onClick={() => setActiveTab('board')}>
                Cancel
              </button>
              <button type="submit" className="auth-submit-btn" disabled={submitting} style={{ width: 'auto', padding: '10px 24px' }}>
                {submitting ? "Registering..." : "Submit SOS Missing Report"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
