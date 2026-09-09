import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Home, LocateFixed, MapPin, Map, AlertCircle, Loader2 } from 'lucide-react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../services/api';

const KERALA_DISTRICTS = [
  "Wayanad", "Idukki", "Malappuram", "Kozhikode", "Palakkad",
  "Pathanamthitta", "Kottayam", "Ernakulam", "Thrissur", "Kannur",
  "Kasaragod", "Alappuzha", "Kollam", "Thiruvananthapuram"
];

// District centroids for automatic district detection
const KERALA_DISTRICTS_CENTROIDS = {
  "Wayanad": { lat: 11.6854, lng: 76.1320 },
  "Idukki": { lat: 9.9189, lng: 77.1025 },
  "Malappuram": { lat: 11.0510, lng: 76.0711 },
  "Kozhikode": { lat: 11.2588, lng: 75.7804 },
  "Palakkad": { lat: 10.7867, lng: 76.6548 },
  "Pathanamthitta": { lat: 9.2648, lng: 76.7870 },
  "Kottayam": { lat: 9.5916, lng: 76.5222 },
  "Ernakulam": { lat: 9.9816, lng: 76.2999 },
  "Thrissur": { lat: 10.5276, lng: 76.2144 },
  "Kannur": { lat: 11.8745, lng: 75.3704 },
  "Kasaragod": { lat: 12.5102, lng: 74.9852 },
  "Alappuzha": { lat: 9.4981, lng: 76.3388 },
  "Kollam": { lat: 8.8932, lng: 76.6141 },
  "Thiruvananthapuram": { lat: 8.5241, lng: 76.9366 }
};

function getClosestDistrict(targetLat, targetLng) {
  let closest = "Wayanad";
  let minD = Infinity;
  for (const [name, coord] of Object.entries(KERALA_DISTRICTS_CENTROIDS)) {
    const dLat = targetLat - coord.lat;
    const dLng = targetLng - coord.lng;
    const dist = dLat * dLat + dLng * dLng;
    if (dist < minD) {
      minD = dist;
      closest = name;
    }
  }
  return closest;
}

// Custom camp pin icon for Leaflet map picker
const campMapPickerIcon = L.divIcon({
  className: 'camp-map-picker-pin-wrapper',
  html: `
    <div class="camp-picker-pin">
      <div class="camp-pin-icon-box">⛺</div>
      <div class="camp-pin-pulse-ring"></div>
    </div>
  `,
  iconSize: [36, 44],
  iconAnchor: [18, 40]
});

function LocationPickerMapEvents({ onLocationPicked }) {
  useMapEvents({
    click(e) {
      onLocationPicked(e.latlng.lat, e.latlng.lng);
    }
  });
  return null;
}

function MapRecenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center && !isNaN(center[0]) && !isNaN(center[1])) {
      map.setView(center, map.getZoom() || 13, { animate: true });
    }
  }, [center, map]);
  return null;
}

export default function AddCampModal({
  isOpen,
  onClose,
  editingShelter = null,
  onCampSaved,
  triggerToast
}) {
  const [name, setName] = useState(editingShelter?.name || '');
  const [district, setDistrict] = useState(editingShelter?.district || 'Wayanad');
  const [lat, setLat] = useState(String(editingShelter?.lat || '11.5510'));
  const [lng, setLng] = useState(String(editingShelter?.lng || '76.1280'));
  const [capacity, setCapacity] = useState(String(editingShelter?.capacity || '300'));
  const [status] = useState(editingShelter?.status || 'active');

  // Location UI states
  const [isLocating, setIsLocating] = useState(false);
  const [showMapPicker, setShowMapPicker] = useState(false);
  const [gpsAccuracy, setGpsAccuracy] = useState(null);
  const [locationSource, setLocationSource] = useState(editingShelter ? 'Existing Facility' : 'Default Coordinates');

  // Amenities
  const initialAmenities = editingShelter?.amenities || {};
  const [medicalPost, setMedicalPost] = useState(editingShelter ? Boolean(initialAmenities.medical_post) : true);
  const [powerBackup, setPowerBackup] = useState(editingShelter ? Boolean(initialAmenities.power_backup) : true);
  const [wheelchairAccessible, setWheelchairAccessible] = useState(editingShelter ? Boolean(initialAmenities.wheelchair_accessible) : true);
  const [childCare, setChildCare] = useState(editingShelter ? Boolean(initialAmenities.child_care) : true);

  // Initial Supplies
  const initialSupplies = editingShelter?.supplies || {};
  const [waterLitres, setWaterLitres] = useState(String(initialSupplies.water_litres ?? '2500'));
  const [foodPackets, setFoodPackets] = useState(String(initialSupplies.food_packets ?? '500'));
  const [medicalKits, setMedicalKits] = useState(String(initialSupplies.medical_kits ?? '30'));
  const [infantSupplies, setInfantSupplies] = useState(String(initialSupplies.infant_supplies ?? '20'));
  const [fuelLitres, setFuelLitres] = useState(String(initialSupplies.fuel_litres ?? '200'));

  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const applyCoordinates = (newLat, newLng, sourceLabel = 'Map Picked') => {
    const numLat = parseFloat(newLat);
    const numLng = parseFloat(newLng);
    if (!isNaN(numLat) && !isNaN(numLng)) {
      setLat(numLat.toFixed(5));
      setLng(numLng.toFixed(5));
      const detectedDistrict = getClosestDistrict(numLat, numLng);
      setDistrict(detectedDistrict);
      setLocationSource(sourceLabel);
    }
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      triggerToast("Geolocation is not supported by your browser.", "error");
      return;
    }

    setIsLocating(true);
    triggerToast("Detecting high-precision device GPS location...", "info");

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocating(false);
        const { latitude, longitude, accuracy } = pos.coords;
        setLat(latitude.toFixed(5));
        setLng(longitude.toFixed(5));
        setGpsAccuracy(Math.round(accuracy));
        const detectedDistrict = getClosestDistrict(latitude, longitude);
        setDistrict(detectedDistrict);
        setLocationSource(`Live GPS (±${Math.round(accuracy)}m)`);
        triggerToast(`✓ Location locked to current GPS: ${latitude.toFixed(4)}°N, ${longitude.toFixed(4)}°E (${detectedDistrict})`, "success");
      },
      (err) => {
        setIsLocating(false);
        let msg = "Could not detect GPS position.";
        if (err.code === 1) msg = "Location permission denied. Please pick on the map or enter coordinates.";
        else if (err.code === 2) msg = "GPS position unavailable. Please pick on the map.";
        else if (err.code === 3) msg = "GPS request timed out.";
        triggerToast(msg, "error");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handleMarkerDragEnd = (e) => {
    const marker = e.target;
    if (marker != null) {
      const position = marker.getLatLng();
      applyCoordinates(position.lat, position.lng, "Map Pin Dragged");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !lat || !lng || !capacity) {
      triggerToast("Please fill in camp name, coordinates, and bed capacity.", "error");
      return;
    }

    setLoading(true);
    const payload = {
      name: name.trim(),
      district,
      lat: parseFloat(lat),
      lng: parseFloat(lng),
      capacity: parseInt(capacity, 10) || 100,
      contact_number: "1077", // Official KSDMA Emergency Control Helpline
      in_charge_name: "",
      in_charge_phone: "",
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
        res = await api.put(`/api/shelters/${editingShelter.id}`, payload);
      } else {
        res = await api.post('/api/shelters/create', payload);
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

  const parsedLat = parseFloat(lat) || 11.5510;
  const parsedLng = parseFloat(lng) || 76.1280;

  const modalContent = (
    <div className="auth-modal-backdrop camp-modal-backdrop" onClick={onClose} style={{ zIndex: 12000 }}>
      <div className="camp-modal-content" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit} className="camp-modal-form-wrapper">
          {/* 1. Fixed Header */}
          <div className="camp-modal-header">
            <div className="camp-modal-header-left">
              <div className="camp-header-icon-box">
                <Home size={20} />
              </div>
              <div>
                <h2 className="camp-modal-title">{editingShelter ? "Edit Relief Camp" : "Register New Relief Camp"}</h2>
                <span className="camp-modal-subtitle">KSDMA Designated Evacuation & Aid Facility</span>
              </div>
            </div>
            <button type="button" className="camp-close-btn" onClick={onClose} aria-label="Close">
              <X size={18} />
            </button>
          </div>

          {/* 2. Scrollable Body */}
          <div className="camp-modal-scrollable-body">
            {/* 1. General Information */}
            <div className="camp-section-label">General Information</div>
          <div className="camp-form-row-2">
            <div className="camp-input-group">
              <label className="camp-field-label">Camp Name *</label>
              <input
                type="text"
                className="camp-text-input"
                placeholder="e.g. Meppadi Govt Higher Secondary Camp"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="camp-input-group">
              <label className="camp-field-label">District *</label>
              <select
                className="camp-select-input"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
              >
                {KERALA_DISTRICTS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 2. Location & Capacity Card */}
          <div className="camp-location-card">
            <div className="camp-location-toolbar">
              <div className="camp-toolbar-actions">
                <button
                  type="button"
                  className={`camp-location-btn ${isLocating ? 'loading' : ''}`}
                  onClick={handleUseCurrentLocation}
                  disabled={isLocating}
                  title="Detect live GPS coordinates and set as camp site"
                >
                  {isLocating ? <Loader2 size={15} className="spin-icon" /> : <LocateFixed size={15} color="#38BDF8" />}
                  <span>{isLocating ? "Acquiring GPS..." : "Use Current Location"}</span>
                </button>

                <button
                  type="button"
                  className={`camp-location-btn ${showMapPicker ? 'active' : ''}`}
                  onClick={() => setShowMapPicker(!showMapPicker)}
                  title="Open interactive map to point and pick camp coordinates"
                >
                  <Map size={15} color="#30D158" />
                  <span>{showMapPicker ? "Hide Map Picker" : "Point on Map"}</span>
                </button>
              </div>

              <div className="camp-location-status-tag">
                <MapPin size={13} color="var(--accent)" />
                <span>{locationSource}: <b>{lat}°N, {lng}°E</b></span>
                {gpsAccuracy && <span className="accuracy-pill">±{gpsAccuracy}m</span>}
              </div>
            </div>

            {/* Interactive Leaflet Point-on-Map Picker */}
            {showMapPicker && (
              <div className="camp-map-picker-container">
                <div className="camp-map-picker-hint">
                  <span>📍 Click anywhere on map or drag the <b>⛺ camp pin</b> to position the relief facility</span>
                  <span style={{ fontSize: '11px', color: '#38BDF8', fontWeight: 600 }}>Detected: {district}</span>
                </div>
                <div className="camp-map-picker-frame">
                  <MapContainer
                    center={[parsedLat, parsedLng]}
                    zoom={14}
                    scrollWheelZoom={true}
                    style={{ height: '100%', width: '100%' }}
                  >
                    <TileLayer
                      url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                      attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                    />
                    <MapRecenter center={[parsedLat, parsedLng]} />
                    <LocationPickerMapEvents onLocationPicked={(newLat, newLng) => applyCoordinates(newLat, newLng, "Map Clicked")} />
                    <Marker
                      position={[parsedLat, parsedLng]}
                      icon={campMapPickerIcon}
                      draggable={true}
                      eventHandlers={{ dragend: handleMarkerDragEnd }}
                    />
                  </MapContainer>
                </div>
              </div>
            )}

            {/* Coordinates & Bed Capacity in Clean Balanced 3 Columns */}
            <div className="camp-form-row-3">
              <div className="camp-input-group">
                <label className="camp-field-label">Latitude (°N) *</label>
                <input
                  type="number"
                  step="0.00001"
                  className="camp-text-input mono-font"
                  value={lat}
                  onChange={(e) => applyCoordinates(e.target.value, lng, "Manual Input")}
                  required
                />
              </div>
              <div className="camp-input-group">
                <label className="camp-field-label">Longitude (°E) *</label>
                <input
                  type="number"
                  step="0.00001"
                  className="camp-text-input mono-font"
                  value={lng}
                  onChange={(e) => applyCoordinates(lat, e.target.value, "Manual Input")}
                  required
                />
              </div>
              <div className="camp-input-group">
                <label className="camp-field-label">Bed Capacity *</label>
                <input
                  type="number"
                  className="camp-text-input"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                  min="10"
                  max="10000"
                  placeholder="e.g. 300"
                  required
                />
              </div>
            </div>
          </div>

          {/* 3. Amenities */}
          <div className="camp-section-label">Available Amenities</div>
          <div className="camp-amenities-grid">
            <label className={`camp-amenity-card ${medicalPost ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={medicalPost}
                onChange={(e) => setMedicalPost(e.target.checked)}
              />
              <span className="amenity-title">🏥 Medical Aid Post</span>
            </label>
            <label className={`camp-amenity-card ${powerBackup ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={powerBackup}
                onChange={(e) => setPowerBackup(e.target.checked)}
              />
              <span className="amenity-title">⚡ Power Generator</span>
            </label>
            <label className={`camp-amenity-card ${wheelchairAccessible ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={wheelchairAccessible}
                onChange={(e) => setWheelchairAccessible(e.target.checked)}
              />
              <span className="amenity-title">♿ Wheelchair Access</span>
            </label>
            <label className={`camp-amenity-card ${childCare ? 'checked' : ''}`}>
              <input
                type="checkbox"
                checked={childCare}
                onChange={(e) => setChildCare(e.target.checked)}
              />
              <span className="amenity-title">👶 Infant / Child Care</span>
            </label>
          </div>

          {/* 4. Initial Emergency Supplies */}
          <div className="camp-section-label">Initial Emergency Supplies Inventory</div>
          <div className="camp-supplies-grid">
            <div className="camp-supply-box">
              <label className="camp-supply-label">💧 Water (L)</label>
              <input
                type="number"
                className="camp-supply-input"
                value={waterLitres}
                onChange={(e) => setWaterLitres(e.target.value)}
                min="0"
              />
            </div>
            <div className="camp-supply-box">
              <label className="camp-supply-label">🍞 Food (Packs)</label>
              <input
                type="number"
                className="camp-supply-input"
                value={foodPackets}
                onChange={(e) => setFoodPackets(e.target.value)}
                min="0"
              />
            </div>
            <div className="camp-supply-box">
              <label className="camp-supply-label">🩹 Medical Kits</label>
              <input
                type="number"
                className="camp-supply-input"
                value={medicalKits}
                onChange={(e) => setMedicalKits(e.target.value)}
                min="0"
              />
            </div>
            <div className="camp-supply-box">
              <label className="camp-supply-label">🍼 Baby Items</label>
              <input
                type="number"
                className="camp-supply-input"
                value={infantSupplies}
                onChange={(e) => setInfantSupplies(e.target.value)}
                min="0"
              />
            </div>
            <div className="camp-supply-box">
              <label className="camp-supply-label">⛽ Fuel (L)</label>
              <input
                type="number"
                className="camp-supply-input"
                value={fuelLitres}
                onChange={(e) => setFuelLitres(e.target.value)}
                min="0"
              />
            </div>
          </div>
          </div>

          {/* 3. Docked Pinned Footer (Always 100% visible, cannot be cut off) */}
          <div className="camp-modal-footer">
            <button
              type="button"
              className="camp-btn-cancel"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="camp-btn-submit"
              disabled={loading}
            >
              {loading ? "Saving Camp..." : (editingShelter ? "Save Changes" : "Register Relief Camp")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : modalContent;
}
