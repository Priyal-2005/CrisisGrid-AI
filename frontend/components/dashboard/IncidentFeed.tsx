"use client";

import { useSystemStore } from "@/store/systemStore";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Flame, HeartPulse, Radiation, MapPin, Shield } from "lucide-react";

export function IncidentFeed() {
  const incidents = useSystemStore((s) => s.incidents);

  const getIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('fire')) return <Flame className="w-3.5 h-3.5 text-orange-500" />;
    if (t.includes('medical') || t.includes('casualty')) return <HeartPulse className="w-3.5 h-3.5 text-red-500" />;
    if (t.includes('chemical') || t.includes('toxic')) return <Radiation className="w-3.5 h-3.5 text-green-500" />;
    return <AlertCircle className="w-3.5 h-3.5 text-yellow-500" />;
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return "bg-critical/15 border-critical/50 text-critical";
      case 'HIGH': return "bg-high/15 border-high/50 text-high";
      case 'MEDIUM': return "bg-medium/15 border-medium/50 text-medium";
      default: return "bg-low/15 border-low/50 text-low";
    }
  };

  // Sort by severity score (highest first)
  const sorted = [...incidents].sort((a, b) => b.severity_score - a.severity_score);

  return (
    <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
      <AnimatePresence mode="popLayout">
        {sorted.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex h-full items-center justify-center text-[10px] text-muted font-mono flex-col gap-2"
          >
            <Shield className="w-5 h-5 text-border" />
            <span>NO ACTIVE THREATS</span>
          </motion.div>
        ) : (
          sorted.map((incident, idx) => (
            <motion.div
              key={incident.id}
              layout
              initial={{ opacity: 0, x: -20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.25, delay: idx * 0.05 }}
              className={`p-2.5 rounded border bg-surface/30 ${
                incident.severity === 'CRITICAL' ? 'critical-glow border-critical/40' : 'border-border/40'
              }`}
            >
              {/* Header: Icon + ID + Severity Badge */}
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  {getIcon(incident.type)}
                  <span className="font-mono text-xs font-bold text-white">{incident.id}</span>
                </div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-mono border font-bold ${getSeverityStyle(incident.severity)}`}>
                  {incident.severity} ({incident.severity_score})
                </span>
              </div>

              {/* Type */}
              <div className="text-[11px] font-semibold text-white/90 mb-0.5">
                {incident.type.toUpperCase()}
              </div>

              {/* Description — truncated */}
              <div className="text-[10px] text-muted mb-1.5 line-clamp-2 leading-snug">
                {incident.description}
              </div>

              {/* Footer: Location + Merged Badge */}
              <div className="flex items-center justify-between text-[9px] text-muted font-mono">
                <div className="flex items-center gap-1">
                  <MapPin className="w-2.5 h-2.5" />
                  {incident.location.toUpperCase()}
                </div>
                {incident.calls_merged > 1 && (
                  <span className="text-primary bg-primary/15 border border-primary/40 px-1.5 py-px rounded-sm animate-pulse">
                    {incident.calls_merged} MERGED
                  </span>
                )}
              </div>

              {/* Deployed Units */}
              {incident.units && incident.units.length > 0 && (
                <div className="mt-1.5 pt-1.5 border-t border-border/30 text-[9px] font-mono flex flex-wrap gap-1">
                  <span className="text-muted">UNITS:</span>
                  {incident.units.map(u => (
                    <span key={u} className="text-high bg-high/10 px-1 rounded">{u}</span>
                  ))}
                </div>
              )}
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  );
}
