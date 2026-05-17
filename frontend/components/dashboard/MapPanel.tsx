"use client";

import { useSystemStore } from "@/store/systemStore";
import { useEffect, useState } from "react";
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

// Delhi Coordinates
const CENTER_LAT = 28.6139;
const CENTER_LNG = 77.2090;

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

export function MapPanel() {
  const { incidents, resources, dispatch_log } = useSystemStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="absolute inset-0 flex items-center justify-center text-xs text-muted font-mono">LOADING MAP ENGINE...</div>;
  }

  const getSeverityColor = (severity: string) => {
    if (severity === 'CRITICAL') return '#FF2D55';
    if (severity === 'HIGH') return '#FF6B35';
    if (severity === 'MEDIUM') return '#FF9500';
    return '#30D158';
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
          
          if (unit && incident && NODE_POSITIONS[unit.location] && NODE_POSITIONS[incident.location]) {
            return (
              <Polyline
                key={`route-${i}`}
                positions={[NODE_POSITIONS[unit.location], NODE_POSITIONS[incident.location]]}
                pathOptions={{ 
                  color: log.status.includes('REROUTED') ? '#FF2D55' : getResourceColor(unit.type), 
                  weight: 2, 
                  opacity: 0.6,
                  dashArray: '5, 5'
                }}
              />
            );
          }
          return null;
        })}

        {/* Incidents Heatmap/Markers */}
        {incidents.map((incident) => {
          const pos = NODE_POSITIONS[incident.location];
          if (!pos) return null;

          return (
            <CircleMarker
              key={incident.id}
              center={pos}
              radius={incident.severity === 'CRITICAL' ? 12 : (incident.severity === 'HIGH' ? 8 : 5)}
              pathOptions={{
                color: getSeverityColor(incident.severity),
                fillColor: getSeverityColor(incident.severity),
                fillOpacity: 0.5,
                weight: 2,
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                <div className="font-mono text-xs">
                  <strong>{incident.id}</strong><br/>
                  {incident.type}<br/>
                  Severity: {incident.severity}
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* Resources Markers */}
        {resources.map((resource) => {
          const pos = NODE_POSITIONS[resource.location];
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
                  <strong>{resource.id}</strong><br/>
                  {resource.type}<br/>
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
