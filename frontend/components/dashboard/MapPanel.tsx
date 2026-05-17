"use client";

import { useSystemStore } from "@/store/systemStore";
import { useEffect, useState, useRef, useMemo } from "react";
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

// ─── Delhi NCR Constants ───
const CENTER: [number, number] = [28.6139, 77.2090];
const ZOOM = 11;
const BOUNDS: [[number, number], [number, number]] = [
  [28.40, 76.85],
  [28.85, 77.45],
];

// ─── Zone → Map Coordinate Lookup ───
const NODE_POSITIONS: Record<string, [number, number]> = {
  connaught_place: [28.6304, 77.2177],
  india_gate: [28.6129, 77.2295],
  aiims: [28.5659, 77.2111],
  airport: [28.5562, 77.1000],
  chandni_chowk: [28.6505, 77.2303],
  lajpat_nagar: [28.5677, 77.2433],
  dwarka: [28.5823, 77.0500],
  rohini: [28.7041, 77.1025],
  karol_bagh: [28.6519, 77.1895],
  saket: [28.5246, 77.2066],
  noida_border: [28.5700, 77.3200],
  gurgaon_border: [28.4595, 77.0266],
};

// Backend zone name → NODE_POSITIONS key
const ZONE_MAP: Record<string, string> = {
  downtown: "connaught_place",
  harbor: "india_gate",
  industrial: "rohini",
  sector7: "saket",
  sector_7: "saket",
  north_grid: "rohini",
  central_park: "india_gate",
  westside: "dwarka",
  port: "gurgaon_border",
  eastside: "noida_border",
  suburbs: "gurgaon_border",
  midtown: "karol_bagh",
  airport: "airport",
  // Pass-through for direct keys
  connaught_place: "connaught_place",
  india_gate: "india_gate",
  aiims: "aiims",
  chandni_chowk: "chandni_chowk",
  lajpat_nagar: "lajpat_nagar",
  dwarka: "dwarka",
  rohini: "rohini",
  karol_bagh: "karol_bagh",
  saket: "saket",
  noida_border: "noida_border",
  gurgaon_border: "gurgaon_border",
};

function resolvePosition(location: string): [number, number] | null {
  if (!location) return null;
  const key = location.toLowerCase().trim().replace(/[\s_-]+/g, "_");
  const mapped = ZONE_MAP[key] || key;
  return NODE_POSITIONS[mapped] || null;
}

// ─── Color helpers ───
const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#FF2D55",
  HIGH: "#FF6B35",
  MEDIUM: "#FF9500",
  LOW: "#30D158",
};

function getIncidentColor(severity: string): string {
  return SEVERITY_COLORS[severity?.toUpperCase()] || "#FF2D55";
}

function getResourceColor(type: string): string {
  if (type.includes("fire")) return "#FF3B30";
  if (type.includes("ambulance")) return "#34C759";
  return "#007AFF";
}

// ═══════════════════════════════════════════════
// MapPanel Component
// ═══════════════════════════════════════════════
export function MapPanel() {
  const incidents = useSystemStore((s) => s.incidents);
  const resources = useSystemStore((s) => s.resources);
  const dispatch_log = useSystemStore((s) => s.dispatch_log);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Memoize route data to prevent unnecessary re-renders
  const routeLines = useMemo(() => {
    if (!dispatch_log.length || !resources.length || !incidents.length) return [];

    return dispatch_log.slice(0, 8).map((log, i) => {
      const unit = resources.find((r) => r.id === log.unit);
      const incident = incidents.find((inc) => inc.id === log.incident);
      if (!unit || !incident) return null;

      const from = resolvePosition(unit.location);
      const to = resolvePosition(incident.location);
      if (!from || !to) return null;

      return {
        key: `route-${log.unit}-${log.incident}-${i}`,
        positions: [from, to] as [[number, number], [number, number]],
        color: log.status?.includes("REROUTED") ? "#FF2D55" : getResourceColor(unit.type),
        isReroute: log.status?.includes("REROUTED") || false,
      };
    }).filter(Boolean);
  }, [dispatch_log, resources, incidents]);

  if (!mounted) {
    return (
      <div className="absolute inset-0 flex items-center justify-center text-xs text-muted font-mono bg-background/80">
        <div className="flex flex-col items-center gap-2">
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
          <span>INITIALIZING MAP ENGINE</span>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 z-0">
      <MapContainer
        center={CENTER}
        zoom={ZOOM}
        minZoom={10}
        maxZoom={15}
        maxBounds={BOUNDS}
        maxBoundsViscosity={1.0}
        style={{ height: "100%", width: "100%", background: "#0A0C10" }}
        zoomControl={false}
        scrollWheelZoom={true}
        dragging={true}
        doubleClickZoom={false}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />

        {/* ─── Dispatch Route Lines ─── */}
        {routeLines.map((route: any) => (
          <Polyline
            key={route.key}
            positions={route.positions}
            pathOptions={{
              color: route.color,
              weight: route.isReroute ? 4 : 3,
              opacity: 0.7,
              dashArray: route.isReroute ? "5, 8" : "10, 10",
              className: "animated-route",
            }}
          />
        ))}

        {/* ─── Incident Markers (red pulsing dots) ─── */}
        {incidents.map((incident) => {
          const pos = resolvePosition(incident.location);
          if (!pos) return null;

          const color = getIncidentColor(incident.severity);
          const radius =
            incident.severity === "CRITICAL" ? 14
            : incident.severity === "HIGH" ? 11
            : 8;

          return (
            <CircleMarker
              key={`inc-${incident.id}`}
              center={pos}
              radius={radius}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: incident.severity === "CRITICAL" ? 0.8 : 0.5,
                weight: 2,
                className:
                  incident.severity === "CRITICAL"
                    ? "animate-pulse-fast"
                    : incident.severity === "HIGH"
                    ? "animate-pulse"
                    : "",
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                <div className="font-mono text-[10px] p-1 min-w-[100px]">
                  <div className="font-bold text-xs" style={{ color }}>{incident.id}</div>
                  <div className="font-bold">{incident.type}</div>
                  <div className="text-gray-400">
                    Severity: <span style={{ color }} className="font-bold">{incident.severity} ({incident.severity_score})</span>
                  </div>
                  <div className="text-gray-500 text-[9px] mt-0.5">{incident.location.toUpperCase()}</div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* ─── Resource Unit Markers (only shown when incidents are active) ─── */}
        {incidents.length > 0 && resources.map((resource) => {
          const pos = resolvePosition(resource.location);
          if (!pos) return null;

          const isDeployed = resource.status === "DISPATCHED";

          return (
            <CircleMarker
              key={`res-${resource.id}`}
              center={pos}
              radius={isDeployed ? 3 : 4}
              pathOptions={{
                color: "#fff",
                fillColor: getResourceColor(resource.type),
                fillOpacity: isDeployed ? 0.3 : 0.9,
                weight: 1,
              }}
            >
              <Tooltip direction="bottom" offset={[0, 10]} opacity={1}>
                <div className="font-mono text-[10px]">
                  <strong>{resource.id}</strong><br />
                  {resource.type}<br />
                  <span className={isDeployed ? "text-orange-500" : "text-green-500"}>
                    {resource.status}
                  </span>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

      </MapContainer>

      {/* Vignette overlay */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(10,12,16,0.9)]"></div>

      {/* Map legend */}
      {incidents.length > 0 && (
        <div className="absolute bottom-3 left-3 z-[1000] pointer-events-none">
          <div className="glass-panel rounded px-2.5 py-1.5 text-[9px] font-mono text-muted space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-critical animate-pulse"></span>
              <span>CRITICAL</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-high"></span>
              <span>HIGH</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-medium"></span>
              <span>MEDIUM</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
