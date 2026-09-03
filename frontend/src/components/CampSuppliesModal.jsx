import { useState } from 'react';
import { X, Package, AlertTriangle, Droplets, Utensils, HeartPulse, Baby, Fuel } from 'lucide-react';
import api from '../services/api';

export default function CampSuppliesModal({
  isOpen,
  onClose,
  shelter,
  onSuppliesUpdated,
  triggerToast
}) {
  const s = shelter?.supplies || {};
  const [waterLitres, setWaterLitres] = useState(s.water_litres ?? 2000);
  const [foodPackets, setFoodPackets] = useState(s.food_packets ?? 500);
  const [medicalKits, setMedicalKits] = useState(s.medical_kits ?? 30);
  const [infantSupplies, setInfantSupplies] = useState(s.infant_supplies ?? 20);
  const [fuelLitres, setFuelLitres] = useState(s.fuel_litres ?? 150);
  const [loading, setLoading] = useState(false);

  if (!isOpen || !shelter) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    const payload = {
      water_litres: parseInt(waterLitres, 10) || 0,
      food_packets: parseInt(foodPackets, 10) || 0,
      medical_kits: parseInt(medicalKits, 10) || 0,
      infant_supplies: parseInt(infantSupplies, 10) || 0,
      fuel_litres: parseInt(fuelLitres, 10) || 0
    };

    try {
      const res = await api.post(`/api/shelters/${shelter.id}/supplies`, {
        supplies: payload
      });

      if (res.data.success) {
        triggerToast(`✓ Emergency supplies updated for '${shelter.name}'`, "success");
        if (onSuppliesUpdated) onSuppliesUpdated(shelter.id, payload);
        onClose();
      } else {
        triggerToast(res.data.error || "Failed to update supplies.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Error connecting to server.", "error");
    } finally {
      setLoading(false);
    }
  };

  const isLowWater = waterLitres < 1000;
  const isLowFood = foodPackets < 200;
  const isLowMedical = medicalKits < 15;

  return (
    <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 12500 }}>
      <div className="supplies-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="auth-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="auth-header-icon" style={{ background: 'rgba(52, 199, 89, 0.15)', color: '#30D158' }}>
              <Package size={22} />
            </div>
            <div>
              <h2 className="auth-title">Camp Supplies & Inventory</h2>
              <span className="auth-subtitle">{shelter.name} ({shelter.district})</span>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Shortage Alert Banner if any resource is low */}
        {(isLowWater || isLowFood || isLowMedical) && (
          <div className="supply-shortage-banner">
            <AlertTriangle size={16} color="#FF9F0A" />
            <span>CRITICAL SHORTAGE: Low threshold detected on essential rations/medical supplies.</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSave} className="camp-form-body">
          <div className="supply-item-row">
            <div className="supply-item-header">
              <div className="supply-icon-title">
                <Droplets size={18} color="#38BDF8" />
                <span>Potable Drinking Water</span>
              </div>
              <span className={`supply-badge ${isLowWater ? 'shortage' : 'adequate'}`}>
                {isLowWater ? 'Low Stock' : 'Adequate'}
              </span>
            </div>
            <div className="supply-input-group">
              <input
                type="number"
                className="auth-input"
                value={waterLitres}
                onChange={(e) => setWaterLitres(e.target.value)}
                min="0"
                required
              />
              <span className="supply-unit">Litres</span>
            </div>
          </div>

          <div className="supply-item-row">
            <div className="supply-item-header">
              <div className="supply-icon-title">
                <Utensils size={18} color="#F59E0B" />
                <span>Cooked Food / Ration Packs</span>
              </div>
              <span className={`supply-badge ${isLowFood ? 'shortage' : 'adequate'}`}>
                {isLowFood ? 'Low Stock' : 'Adequate'}
              </span>
            </div>
            <div className="supply-input-group">
              <input
                type="number"
                className="auth-input"
                value={foodPackets}
                onChange={(e) => setFoodPackets(e.target.value)}
                min="0"
                required
              />
              <span className="supply-unit">Packets</span>
            </div>
          </div>

          <div className="supply-item-row">
            <div className="supply-item-header">
              <div className="supply-icon-title">
                <HeartPulse size={18} color="#EF4444" />
                <span>Emergency Medical & Trauma Kits</span>
              </div>
              <span className={`supply-badge ${isLowMedical ? 'shortage' : 'adequate'}`}>
                {isLowMedical ? 'Low Stock' : 'Adequate'}
              </span>
            </div>
            <div className="supply-input-group">
              <input
                type="number"
                className="auth-input"
                value={medicalKits}
                onChange={(e) => setMedicalKits(e.target.value)}
                min="0"
                required
              />
              <span className="supply-unit">Kits</span>
            </div>
          </div>

          <div className="supply-item-row">
            <div className="supply-item-header">
              <div className="supply-icon-title">
                <Baby size={18} color="#EC4899" />
                <span>Infant Nutrition & Child Supplies</span>
              </div>
              <span className="supply-badge adequate">Standard</span>
            </div>
            <div className="supply-input-group">
              <input
                type="number"
                className="auth-input"
                value={infantSupplies}
                onChange={(e) => setInfantSupplies(e.target.value)}
                min="0"
                required
              />
              <span className="supply-unit">Units</span>
            </div>
          </div>

          <div className="supply-item-row">
            <div className="supply-item-header">
              <div className="supply-icon-title">
                <Fuel size={18} color="#A855F7" />
                <span>Generator Diesel Fuel</span>
              </div>
              <span className="supply-badge adequate">Power Ready</span>
            </div>
            <div className="supply-input-group">
              <input
                type="number"
                className="auth-input"
                value={fuelLitres}
                onChange={(e) => setFuelLitres(e.target.value)}
                min="0"
                required
              />
              <span className="supply-unit">Litres</span>
            </div>
          </div>

          <div className="camp-modal-footer" style={{ marginTop: '16px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="auth-submit-btn" disabled={loading} style={{ width: 'auto', padding: '10px 24px' }}>
              {loading ? "Updating Supplies..." : "Save Supplies"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
