import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

export default function HazardHeatmapLayer({ points = [], isVisible = false, opacity = 0.8 }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !isVisible || !Array.isArray(points) || points.length === 0) return;

    // Filter valid [lat, lng, intensity] tuples
    const validPoints = points.filter(p => Array.isArray(p) && p.length >= 2 && !isNaN(p[0]) && !isNaN(p[1]));
    if (validPoints.length === 0) return;

    const heatLayer = L.heatLayer(validPoints, {
      radius: 32,
      blur: 22,
      maxZoom: 12,
      max: 1.0,
      minOpacity: 0.25,
      gradient: {
        0.15: '#38BDF8', // Cyan/Sky
        0.35: '#30D158', // Green (Safe/Low)
        0.55: '#F59E0B', // Amber (Moderate Risk)
        0.75: '#EF4444', // Red (High Landslide Hazard)
        1.00: '#991B1B'  // Deep Crimson (Severe Escarpment Torrent)
      }
    });

    heatLayer.addTo(map);

    return () => {
      try {
        map.removeLayer(heatLayer);
      } catch {
        // Safe unmount
      }
    };
  }, [map, isVisible, points, opacity]);

  return null;
}
