"use client";

import { useSystemStore } from "@/store/systemStore";
import { useEffect, useState } from "react";
import 'leaflet/dist/leaflet.css';
// Dynamic import for react-leaflet to avoid SSR issues
import dynamic from 'next/dynamic';

const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);
const CircleMarker = dynamic(
  () => import('react-leaflet').then((mod) => mod.CircleMarker),
  { ssr: false }
);
const Tooltip = dynamic(
  () => import('react-leaflet').then((mod) => mod.Tooltip),
  { ssr: false }
);
const Polyline = dynamic(
  () => import('react-leaflet').then((mod) => mod.Polyline),
  { ssr: false }
);

// Delhi Coordinates & Constraints
const CENTER_LAT = 28.6139;
const CENTER_LNG = 77.2090;
const DELHI_BOUNDS = [
  [28.40, 76.85], // South-West
  [28.85, 77.45]  // North-East
];

// Hardcoded node positions for visualization
const NODE_POSITIONS: Record<string, [number, number]> = {
  "connaught_place": [28.6304, 77.2177],
  "india_gate": [28.6129, 77.2295],
  "aiims": [28.5659, 77.2111],
  "airport": [28.5562, 77.1000],
  "chandni_chowk": [28.6505, 77.2303],
  "lajpat_nagar": [28.5677, 77.2433],
  "dwarka": [28.5823, 77.0500],
  "rohini": [28.7041, 77.1025],
  "karol_bagh": [28.6519, 77.1895],
  "saket": [28.5246, 77.2066],
  "noida_border": [28.5700, 77.3200],
  "gurgaon_border": [28.4595, 77.0266],
};

// Map backend zones (Title Case or lowercase) to hardcoded Delhi NODE_POSITIONS keys
const getNormalizedLocationKey = (location: string): string => {
  if (!location) return "connaught_place";
  const loc = location.toLowerCase().trim().replace(/[\s_-]+/g, '_');
  
  const mapping: Record<string, string> = {
    'downtown': 'connaught_place',
    'harbor': 'india_gate',
    'industrial': 'rohini',
    'sector7': 'saket',
    'sector_7': 'saket',
    'north_grid': 'rohini',
    'central_park': 'india_gate',
    'westside': 'dwarka',
    'port': 'gurgaon_border',
    'eastside': 'noida_border',
    'suburbs': 'gurgaon_border',
    'midtown': 'karol_bagh',
    'airport': 'airport',
    // already direct
    'connaught_place': 'connaught_place',
    'india_gate': 'india_gate',
    'aiims': 'aiims',
    'chandni_chowk': 'chandni_chowk',
    'lajpat_nagar': 'lajpat_nagar',
    'dwarka': 'dwarka',
    'rohini': 'rohini',
    'karol_bagh': 'karol_bagh',
    'saket': 'saket',
    'noida_border': 'noida_border',
    'gurgaon_border': 'gurgaon_border',
  };

  return mapping[loc] || loc;
};

export function MapPanel() {
  const { incidents, resources, dispatch_log } = useSystemStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="absolute inset-0 flex items-center justify-center text-xs text-muted font-mono">LOADING MAP ENGINE...</div>;
  }

  const getTypeColor = (type: string) => {
    // Return bright EOC tactical red for all incident dots as requested by the user
    return '#FF2D55';
  };

  const getSeverityPulseClass = (severity: string) => {
    if (severity === 'CRITICAL') return 'animate-pulse-fast';
    if (severity === 'HIGH') return 'animate-pulse';
    return '';
  };

  const getResourceColor = (type: string) => {
    if (type.includes('fire')) return '#FF3B30';
    if (type.includes('ambulance')) return '#34C759';
    return '#007AFF';
  };

  return (
    <div className="absolute inset-0 z-0">
      <MapContainer
        center={[CENTER_LAT, CENTER_LNG]}
        zoom={11}
        minZoom={10}
        maxZoom={15}
        maxBounds={DELHI_BOUNDS as any}
        maxBoundsViscosity={1.0}
        style={{ height: '100%', width: '100%', background: '#0A0C10' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />

        {/* Draw routing lines based on dispatch_log */}
        {dispatch_log.slice(0, 5).map((log, i) => {
          const unit = resources.find(r => r.id === log.unit);
          const incident = incidents.find(inc => inc.id === log.incident);

          const unitKey = unit ? getNormalizedLocationKey(unit.location) : "";
          const incKey = incident ? getNormalizedLocationKey(incident.location) : "";

          if (unit && incident && NODE_POSITIONS[unitKey] && NODE_POSITIONS[incKey]) {
            return (
              <Polyline
                key={`route-${i}`}
                positions={[NODE_POSITIONS[unitKey], NODE_POSITIONS[incKey]]}
                pathOptions={{
                  color: log.status.includes('REROUTED') ? '#FF2D55' : getResourceColor(unit.type),
                  weight: 3,
                  opacity: 0.8,
                  dashArray: '10, 10',
                  className: 'animated-route'
                }}
              />
            );
          }
          return null;
        })}

        {/* Incidents Heatmap/Markers */}
        {incidents.map((incident) => {
          const locKey = getNormalizedLocationKey(incident.location);
          const pos = NODE_POSITIONS[locKey];
          if (!pos) return null;

          return (
            <CircleMarker
              key={incident.id}
              center={pos}
              radius={incident.severity === 'CRITICAL' ? 14 : (incident.severity === 'HIGH' ? 10 : 7)}
              pathOptions={{
                color: getTypeColor(incident.type),
                fillColor: getTypeColor(incident.type),
                fillOpacity: incident.severity === 'CRITICAL' ? 0.8 : 0.5,
                weight: 2,
                className: getSeverityPulseClass(incident.severity)
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1} className="bg-surface border-border text-white font-mono text-xs">
                <div className="p-1">
                  <strong className="text-critical">{incident.id}</strong><br />
                  <span className="text-white font-bold">{incident.type}</span><br />
                  <span className="text-muted">Severity: </span>
                  <span className={incident.severity === 'CRITICAL' ? 'text-critical font-bold' : incident.severity === 'HIGH' ? 'text-high font-bold' : 'text-primary'}>
                    {incident.severity}
                  </span>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* Resources Markers */}
        {resources.map((resource) => {
          const locKey = getNormalizedLocationKey(resource.location);
          const pos = NODE_POSITIONS[locKey];
          if (!pos) return null;

          return (
            <CircleMarker
              key={resource.id}
              center={pos}
              radius={4}
              pathOptions={{
                color: '#fff',
                fillColor: getResourceColor(resource.type),
                fillOpacity: resource.status === 'AVAILABLE' ? 1 : 0.3,
                weight: 1,
              }}
            >
              <Tooltip direction="bottom" offset={[0, 10]} opacity={1}>
                <div className="font-mono text-xs">
                  <strong>{resource.id}</strong><br />
                  {resource.type}<br />
                  Status: {resource.status}
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

      </MapContainer>

      {/* Overlay gradient to blend map edges into the dark dashboard */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_40px_rgba(10,12,16,1)]"></div>
    </div>
  );
}
