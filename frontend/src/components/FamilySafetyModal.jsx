import { useState, useEffect } from 'react';
import { X, Users, Heart, Send, Plus, Trash2, CheckCircle, Search, Phone, MapPin, Share2 } from 'lucide-react';
import axios from 'axios';

export default function FamilySafetyModal({
  isOpen,
  onClose,
  user,
  token,
  currentCoords,
  triggerToast
}) {
  const [activeTab, setActiveTab] = useState('circle'); // 'circle' | 'lookup'
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pingLoading, setPingLoading] = useState(false);

  // Add Contact Form
  const [showAddForm, setShowAddForm] = useState(false);
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [relationship, setRelationship] = useState('Family');

  // Ping Result
  const [lastPingResult, setLastPingResult] = useState(null);

  // Public Lookup
  const [lookupPhone, setLookupPhone] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  const fetchContacts = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await axios.get('http://127.0.0.1:5000/api/user/family-contacts', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.data.success) {
        setContacts(res.data.contacts);
      }
    } catch (err) {
      console.log("Contacts fetch gap.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && token) {
      fetchContacts();
    }
  }, [isOpen, token]);

  if (!isOpen) return null;

  const handleAddContact = async (e) => {
    e.preventDefault();
    if (!contactName || !contactPhone) {
      triggerToast("Name and phone number are required.", "error");
      return;
    }

    try {
      const res = await axios.post('http://127.0.0.1:5000/api/user/family-contacts', {
        contact_name: contactName,
        contact_phone: contactPhone,
        relationship
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.data.success) {
        triggerToast("✓ Emergency contact added to your Family Circle!", "success");
        setContactName('');
        setContactPhone('');
        setShowAddForm(false);
        fetchContacts();
      } else {
        triggerToast(res.data.error || "Failed to add contact.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Error adding contact.", "error");
    }
  };

  const handleDeleteContact = async (contactId) => {
    try {
      const res = await axios.delete(`http://127.0.0.1:5000/api/user/family-contacts/${contactId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.data.success) {
        triggerToast("Contact removed from Family Circle.", "info");
        fetchContacts();
      }
    } catch (err) {
      triggerToast("Failed to remove contact.", "error");
    }
  };

  const handleTriggerSafePing = async () => {
    const lat = user?.lat || currentCoords?.lat || 11.5542;
    const lng = user?.lng || currentCoords?.lng || 76.1308;

    setPingLoading(true);
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/user/ping-safe', {
        lat,
        lng,
        status_message: "Safe and sheltered. All nominal."
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.data.success) {
        setLastPingResult(res.data);
        triggerToast("✅ 'I Am Safe' broadcast recorded & WhatsApp beacon generated!", "success");
        // Open WhatsApp broadcast
        if (res.data.whatsapp_share_url) {
          window.open(res.data.whatsapp_share_url, '_blank');
        }
      }
    } catch (err) {
      triggerToast("Error triggering safety ping.", "error");
    } finally {
      setPingLoading(false);
    }
  };

  const handleLookup = async (e) => {
    e.preventDefault();
    if (!lookupPhone) return;
    setLookupLoading(true);
    setLookupResult(null);

    try {
      const res = await axios.get(`http://127.0.0.1:5000/api/public/check-status?phone=${encodeURIComponent(lookupPhone)}`);
      if (res.data.success) {
        setLookupResult(res.data.record);
      } else {
        triggerToast("No citizen check-in record found for this phone.", "info");
      }
    } catch (err) {
      triggerToast("No citizen check-in record found for this phone.", "info");
    } finally {
      setLookupLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 12000 }}>
      <div className="family-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="auth-header-icon" style={{ background: 'rgba(236, 72, 153, 0.15)', color: '#EC4899' }}>
              <Heart size={22} />
            </div>
            <div>
              <h2 className="auth-title">Family Safety Circle</h2>
              <span className="auth-subtitle">1-Tap Citizen Welfare & Emergency Check-In</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="family-tabs">
          <button
            className={`family-tab-btn ${activeTab === 'circle' ? 'active' : ''}`}
            onClick={() => setActiveTab('circle')}
          >
            <Users size={16} />
            <span>My Safety Circle & Ping</span>
          </button>
          <button
            className={`family-tab-btn ${activeTab === 'lookup' ? 'active' : ''}`}
            onClick={() => setActiveTab('lookup')}
          >
            <Search size={16} />
            <span>Citizen Status Lookup</span>
          </button>
        </div>

        {/* Tab 1: Circle & Ping */}
        {activeTab === 'circle' && (
          <div className="family-tab-body">
            {/* Big 1-Tap Ping Card */}
            <div className="safe-ping-card">
              <div className="safe-ping-header">
                <div>
                  <h3 style={{ margin: 0, fontSize: '15px', fontWeight: '800', color: '#FFF' }}>
                    1-Tap "I Am Safe" Broadcast
                  </h3>
                  <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'rgba(255, 255, 255, 0.7)' }}>
                    Sends instant GPS coordinates, shelter location, and safety confirmation to your circle via WhatsApp & SMS.
                  </p>
                </div>
              </div>

              <button
                className="btn-i-am-safe"
                onClick={handleTriggerSafePing}
                disabled={pingLoading || !token}
              >
                <CheckCircle size={20} />
                <span>{pingLoading ? "Broadcasting Ping..." : (token ? "BROADCAST 'I AM SAFE' NOW" : "Login to Broadcast Ping")}</span>
              </button>

              {lastPingResult && (
                <div className="ping-success-box">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <CheckCircle size={16} color="#30D158" />
                    <strong style={{ fontSize: '13px', color: '#30D158' }}>Status Broadcasted!</strong>
                  </div>
                  <pre style={{ fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0 }}>
                    {lastPingResult.safety_summary}
                  </pre>
                  {lastPingResult.whatsapp_share_url && (
                    <a
                      href={lastPingResult.whatsapp_share_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-share-wa"
                      style={{ marginTop: '8px', display: 'inline-flex' }}
                    >
                      <Share2 size={14} />
                      <span>Re-Share to WhatsApp Group</span>
                    </a>
                  )}
                </div>
              )}
            </div>

            {/* Emergency Contacts List */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', marginBottom: '8px' }}>
              <span className="form-section-label" style={{ margin: 0 }}>Emergency Contacts ({contacts.length}/3)</span>
              {contacts.length < 3 && !showAddForm && (
                <button
                  className="btn-add-contact-pill"
                  onClick={() => setShowAddForm(true)}
                  disabled={!token}
                >
                  <Plus size={14} />
                  <span>Add Contact</span>
                </button>
              )}
            </div>

            {/* Add Contact Inline Form */}
            {showAddForm && (
              <form onSubmit={handleAddContact} className="add-contact-inline-form">
                <div className="form-grid-3">
                  <input
                    type="text"
                    className="auth-input"
                    placeholder="Name (e.g. Appa / Amma)"
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    required
                  />
                  <input
                    type="tel"
                    className="auth-input"
                    placeholder="Phone (+91...)"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    required
                  />
                  <select
                    className="auth-input"
                    value={relationship}
                    onChange={(e) => setRelationship(e.target.value)}
                  >
                    <option value="Parent">Parent</option>
                    <option value="Spouse">Spouse</option>
                    <option value="Sibling">Sibling</option>
                    <option value="Child">Child</option>
                    <option value="Friend">Friend / Neighbour</option>
                  </select>
                </div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowAddForm(false)} style={{ padding: '6px 14px', fontSize: '12px' }}>
                    Cancel
                  </button>
                  <button type="submit" className="auth-submit-btn" style={{ width: 'auto', padding: '6px 16px', fontSize: '12px' }}>
                    Save Contact
                  </button>
                </div>
              </form>
            )}

            {/* Contacts Cards */}
            {contacts.length === 0 && !showAddForm && (
              <div className="empty-contacts-state">
                <Users size={32} color="var(--text-tertiary)" />
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  No family contacts registered yet. Add your family members to notify them in 1 tap during disasters.
                </p>
              </div>
            )}

            <div className="contacts-grid">
              {contacts.map(c => (
                <div key={c.id} className="contact-card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="contact-avatar">
                      {c.contact_name ? c.contact_name[0].toUpperCase() : 'F'}
                    </div>
                    <div>
                      <div style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>{c.contact_name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{c.relationship} • {c.contact_phone}</div>
                    </div>
                  </div>
                  <button
                    className="btn-delete-contact"
                    onClick={() => handleDeleteContact(c.id)}
                    title="Remove Contact"
                  >
                    <Trash2 size={14} color="#EF4444" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: Public Lookup */}
        {activeTab === 'lookup' && (
          <div className="family-tab-body">
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 0 }}>
              Search for any citizen in Kerala disaster sectors to view their latest "I Am Safe" check-in telemetry and shelter destination.
            </p>

            <form onSubmit={handleLookup} className="lookup-search-bar" style={{ display: 'flex', gap: '8px' }}>
              <input
                type="tel"
                className="auth-input"
                placeholder="Enter Registered Mobile Number (e.g. +91 9447...)"
                value={lookupPhone}
                onChange={(e) => setLookupPhone(e.target.value)}
                required
                style={{ flex: 1 }}
              />
              <button type="submit" className="auth-submit-btn" disabled={lookupLoading} style={{ width: 'auto', padding: '10px 20px' }}>
                <Search size={16} />
                <span>{lookupLoading ? "Searching..." : "Lookup Status"}</span>
              </button>
            </form>

            {lookupResult && (
              <div className="lookup-result-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <CheckCircle size={20} color="#30D158" />
                  <div>
                    <div style={{ fontWeight: '800', fontSize: '15px', color: 'var(--text-primary)' }}>{lookupResult.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>District: {lookupResult.district || 'Kerala'} • {lookupResult.phone}</div>
                  </div>
                </div>

                <div className="lookup-details-grid">
                  <div className="lookup-detail-item">
                    <span className="lookup-lbl">Latest Welfare Status:</span>
                    <span className="lookup-val" style={{ color: '#30D158', fontWeight: '700' }}>
                      {lookupResult.last_ping_status || "Registered Safe on TerraRisk Grid"}
                    </span>
                  </div>
                  <div className="lookup-detail-item">
                    <span className="lookup-lbl">Last Check-In Time:</span>
                    <span className="lookup-val">
                      {lookupResult.last_ping_at ? new Date(lookupResult.last_ping_at).toLocaleString() : "Recent Check-in"}
                    </span>
                  </div>
                  {lookupResult.last_ping_lat && (
                    <div className="lookup-detail-item">
                      <span className="lookup-lbl">Sector Coordinates:</span>
                      <span className="lookup-val">
                        ({lookupResult.last_ping_lat.toFixed(4)}°N, {lookupResult.last_ping_lng.toFixed(4)}°E)
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
