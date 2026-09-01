import { X, Phone, Shield, Flame, Ambulance, Compass, Radio } from 'lucide-react';

const HELPLINES = [
  {
    number: "112",
    title: "National Emergency Response (ERSS)",
    desc: "Single emergency number for Police, Fire, Ambulance & Disaster Response",
    badge: "24/7 Toll-Free",
    color: "#EF4444",
    icon: Shield
  },
  {
    number: "1077",
    title: "District Disaster Management (DDMA)",
    desc: "District Collectorate 24/7 Disaster Control Room (Wayanad / Idukki / Malappuram)",
    badge: "Local Taluk Response",
    color: "#F59E0B",
    icon: Compass
  },
  {
    number: "1070",
    title: "State Emergency Operations (SEOC)",
    desc: "Kerala State Disaster Management Authority (KSDMA) Headquarters",
    badge: "State Command Cell",
    color: "#38BDF8",
    icon: Radio
  },
  {
    number: "108",
    title: "Emergency Medical Ambulance",
    desc: "Kanivu 108 Free Emergency Ambulance & Critical Trauma Service",
    badge: "Medical Transit",
    color: "#30D158",
    icon: Ambulance
  },
  {
    number: "101",
    title: "Kerala Fire & Rescue Services",
    desc: "Search & rescue, water extraction, debris clearing, and flood evacuation",
    badge: "Rescue Taskforce",
    color: "#F97316",
    icon: Flame
  },
  {
    number: "100",
    title: "Kerala Police Control Room",
    desc: "Law enforcement, evacuation enforcement, and traffic corridor clearance",
    badge: "Public Safety",
    color: "#6366F1",
    icon: Shield
  },
  {
    number: "1076",
    title: "Forest Dept Wildlife & Forest Fire",
    desc: "Forest fringes, ghat roads, and high-altitude mountain rescues",
    badge: "Forest Unit",
    color: "#10B981",
    icon: Compass
  }
];

export default function EmergencyHelplinesModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 14000 }}>
      <div className="helpline-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="helpline-icon-badge">
              <Phone size={20} color="#38BDF8" />
            </div>
            <div>
              <h2 className="auth-title">Emergency Helplines Directory</h2>
              <span className="auth-subtitle">Kerala 24/7 Disaster Control Operations</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="helplines-scroll-list">
          {HELPLINES.map((item, idx) => {
            const IconComponent = item.icon;
            return (
              <div key={idx} className="helpline-item-card" style={{ borderLeft: `4px solid ${item.color}` }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <div className="helpline-num-badge" style={{ background: item.color }}>
                    <IconComponent size={16} color="#FFF" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                      <span className="helpline-item-title">{item.title}</span>
                      <span className="helpline-badge-pill" style={{ color: item.color, borderColor: item.color }}>
                        {item.badge}
                      </span>
                    </div>
                    <p className="helpline-item-desc">{item.desc}</p>
                  </div>
                </div>

                <a
                  href={`tel:${item.number}`}
                  className="helpline-dial-action-btn"
                  style={{ background: item.color }}
                >
                  <Phone size={13} />
                  <span>Dial {item.number}</span>
                </a>
              </div>
            );
          })}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '10.5px', color: 'var(--text-secondary)' }}>
          <span>✓ Works offline via cellular carrier</span>
          <button onClick={onClose} className="ios-button" style={{ padding: '6px 14px', fontSize: '11px' }}>
            Close Directory
          </button>
        </div>
      </div>
    </div>
  );
}
