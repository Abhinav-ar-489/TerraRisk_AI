import { useState, useEffect } from 'react';
import { X, Home, MapPin, Phone, Users, Shield, Plus, CheckCircle, Package } from 'lucide-react';
import axios from 'axios';

const KERALA_DISTRICTS = [
  "Wayanad", "Idukki", "Malappuram", "Kozhikode", "Palakkad",
  "Pathanamthitta", "Kottayam", "Ernakulam", "Thrissur", "Kannur", "Kasaragod"
];

export default function AddCampModal({
  isOpen,
  onClose,
  token,
  editingShelter = null,
  onCampSaved,
  triggerToast
}) {
  const [name, setName] = useState('');
  const [district, setDistrict] = useState('Wayanad');
  const [lat, setLat] = useState('11.5510');
  const [lng, setLng] = useState('76.1280');
  const [capacity, setCapacity] = useState('300');
  const [contactNumber, setContactNumber] = useState('');
  const [inChargeName, setInChargeName] = useState('');
  const [inChargePhone, setInChargePhone] = useState('');
  const [status, setStatus] = useState('active');

  // Amenities
  const [medicalPost, setMedicalPost] = useState(true);
  const [powerBackup, setPowerBackup] = useState(true);
  const [wheelchairAccessible, setWheelchairAccessible] = useState(true);
  const [childCare, setChildCare] = useState(true);

  // Initial Supplies
  const [waterLitres, setWaterLitres] = useState('2500');
  const [foodPackets, setFoodPackets] = useState('500');
  const [medicalKits, setMedicalKits] = useState('30');
  const [infantSupplies, setInfantSupplies] = useState('20');
  const [fuelLitres, setFuelLitres] = useState('200');

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (editingShelter) {
      setName(editingShelter.name || '');
      setDistrict(editingShelter.district || 'Wayanad');
      setLat(String(editingShelter.lat || '11.5510'));
      setLng(String(editingShelter.lng || '76.1280'));
      setCapacity(String(editingShelter.capacity || '300'));
      setContactNumber(editingShelter.contact_number || '');
      setInChargeName(editingShelter.in_charge_name || '');
      setInChargePhone(editingShelter.in_charge_phone || '');
      setStatus(editingShelter.status || 'active');

      const amenities = editingShelter.amenities || {};
      setMedicalPost(Boolean(amenities.medical_post));
      setPowerBackup(Boolean(amenities.power_backup));
      setWheelchairAccessible(Boolean(amenities.wheelchair_accessible));
      setChildCare(Boolean(amenities.child_care));

      const supplies = editingShelter.supplies || {};
      setWaterLitres(String(supplies.water_litres ?? '2500'));
      setFoodPackets(String(supplies.food_packets ?? '500'));
      setMedicalKits(String(supplies.medical_kits ?? '30'));
      setInfantSupplies(String(supplies.infant_supplies ?? '20'));
      setFuelLitres(String(supplies.fuel_litres ?? '200'));
    } else {
      setName('');
      setDistrict('Wayanad');
      setLat('11.5510');
      setLng('76.1280');
      setCapacity('300');
      setContactNumber('+91 4936 282220');
      setInChargeName('');
      setInChargePhone('');
      setStatus('active');
    }
  }, [editingShelter, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !lat || !lng || !capacity || !contactNumber) {
      triggerToast("Please fill in all mandatory camp details.", "error");
      return;
    }

    setLoading(true);
    const payload = {
      name,
      district,
      lat: parseFloat(lat),
      lng: parseFloat(lng),
      capacity: parseInt(capacity, 10),
      contact_number: contactNumber,
      in_charge_name: inChargeName,
      in_charge_phone: inChargePhone,
      status,
      amenities: {
        medical_post: medicalPost,
        power_backup: powerBackup,
        wheelchair_accessible: wheelchairAccessible,
        child_care: childCare
      },
      supplies: {
        water_litres: parseInt(waterLitres, 10) || 0,
        food_packets: parseInt(foodPackets, 10) || 0,
        medical_kits: parseInt(medicalKits, 10) || 0,
        infant_supplies: parseInt(infantSupplies, 10) || 0,
        fuel_litres: parseInt(fuelLitres, 10) || 0
      }
    };

    try {
      let res;
      if (editingShelter) {
        res = await axios.put(`http://127.0.0.1:5000/api/shelters/${editingShelter.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } else {
        res = await axios.post('http://127.0.0.1:5000/api/shelters/create', payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }

      if (res.data.success) {
        triggerToast(
          editingShelter ? `✓ Relief camp '${name}' updated.` : `✓ Relief camp '${name}' registered on disaster grid.`,
          "success"
        );
        if (onCampSaved) onCampSaved(res.data.shelter);
        onClose();
      } else {
        triggerToast(res.data.error || "Failed to save relief camp.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Error connecting to shelter service.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 12000 }}>
      <div className="camp-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="auth-header-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38BDF8' }}>
              <Home size={22} />
            </div>
            <div>
              <h2 className="auth-title">{editingShelter ? "Edit Relief Camp" : "Register New Relief Camp"}</h2>
              <span className="auth-subtitle">KSDMA Designated Evacuation & Aid Facility</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="camp-form-body">
          {/* 1. Basic Info */}
          <div className="form-section-label">General Information</div>
          <div className="form-grid-2">
            <div className="auth-field">
              <label className="auth-label">Camp Name *</label>
              <input
                type="text"
                className="auth-input"
                placeholder="e.g. Meppadi Govt Higher Secondary Camp"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">District *</label>
              <select
                className="auth-input"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
              >
                {KERALA_DISTRICTS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-grid-3">
            <div className="auth-field">
              <label className="auth-label">Latitude (°N) *</label>
              <input
                type="number"
                step="0.0001"
                className="auth-input"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                required
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">Longitude (°E) *</label>
              <input
                type="number"
                step="0.0001"
                className="auth-input"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                required
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">Bed Capacity *</label>
              <input
                type="number"
                className="auth-input"
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
                min="10"
                max="5000"
                required
              />
            </div>
          </div>

          {/* 2. In-Charge & Contacts */}
          <div className="form-section-label" style={{ marginTop: '12px' }}>Operational Authority & Contacts</div>
          <div className="form-grid-3">
            <div className="auth-field">
              <label className="auth-label">Camp Helpline *</label>
              <input
                type="tel"
                className="auth-input"
                placeholder="+91 4936 282220"
                value={contactNumber}
                onChange={(e) => setContactNumber(e.target.value)}
                required
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">In-Charge Officer</label>
              <input
                type="text"
                className="auth-input"
                placeholder="e.g. Rajesh Kumar (Tahsildar)"
                value={inChargeName}
                onChange={(e) => setInChargeName(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">In-Charge Mobile</label>
              <input
                type="tel"
                className="auth-input"
                placeholder="+91 94471 23456"
                value={inChargePhone}
                onChange={(e) => setInChargePhone(e.target.value)}
              />
            </div>
          </div>

          {/* 3. Amenities */}
          <div className="form-section-label" style={{ marginTop: '12px' }}>Available Amenities</div>
          <div className="amenities-checkbox-grid">
            <label className="amenity-checkbox-card">
              <input
                type="checkbox"
                checked={medicalPost}
                onChange={(e) => setMedicalPost(e.target.checked)}
              />
              <span>🏥 Medical Aid Post</span>
            </label>
            <label className="amenity-checkbox-card">
              <input
                type="checkbox"
                checked={powerBackup}
                onChange={(e) => setPowerBackup(e.target.checked)}
              />
              <span>⚡ Power Generator</span>
            </label>
            <label className="amenity-checkbox-card">
              <input
                type="checkbox"
                checked={wheelchairAccessible}
                onChange={(e) => setWheelchairAccessible(e.target.checked)}
              />
              <span>♿ Wheelchair Access</span>
            </label>
            <label className="amenity-checkbox-card">
              <input
                type="checkbox"
                checked={childCare}
                onChange={(e) => setChildCare(e.target.checked)}
              />
              <span>👶 Infant / Child Care</span>
            </label>
          </div>

          {/* 4. Initial Emergency Supplies */}
          <div className="form-section-label" style={{ marginTop: '12px' }}>Initial Emergency Supplies Inventory</div>
          <div className="form-grid-5">
            <div className="auth-field">
              <label className="auth-label">💧 Water (L)</label>
              <input
                type="number"
                className="auth-input"
                value={waterLitres}
                onChange={(e) => setWaterLitres(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">🍞 Food (Packs)</label>
              <input
                type="number"
                className="auth-input"
                value={foodPackets}
                onChange={(e) => setFoodPackets(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">🩹 Medical Kits</label>
              <input
                type="number"
                className="auth-input"
                value={medicalKits}
                onChange={(e) => setMedicalKits(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">🍼 Baby Items</label>
              <input
                type="number"
                className="auth-input"
                value={infantSupplies}
                onChange={(e) => setInfantSupplies(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label">⛽ Fuel (L)</label>
              <input
                type="number"
                className="auth-input"
                value={fuelLitres}
                onChange={(e) => setFuelLitres(e.target.value)}
              />
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="camp-modal-footer" style={{ marginTop: '18px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="auth-submit-btn" disabled={loading} style={{ width: 'auto', padding: '10px 24px' }}>
              {loading ? "Saving Camp..." : (editingShelter ? "Save Changes" : "Register Relief Camp")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
