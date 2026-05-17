"use client";

import { useSystemStore } from "@/store/systemStore";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Flame, HeartPulse, Radiation, MapPin, Users } from "lucide-react";

export function IncidentFeed() {
  const { incidents } = useSystemStore();

  const getIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('fire')) return <Flame className="w-4 h-4 text-orange-500" />;
    if (t.includes('medical') || t.includes('casualty')) return <HeartPulse className="w-4 h-4 text-red-500" />;
    if (t.includes('chemical') || t.includes('toxic')) return <Radiation className="w-4 h-4 text-green-500" />;
    return <AlertCircle className="w-4 h-4 text-yellow-500" />;
  };

  const getSeverityColor = (score: number) => {
    if (score >= 86) return "bg-critical/20 border-critical text-critical";
    if (score >= 66) return "bg-high/20 border-high text-high";
    if (score >= 36) return "bg-medium/20 border-medium text-medium";
    return "bg-low/20 border-low text-low";
  };

  // Sort by highest severity score first
  const sortedIncidents = [...incidents].sort((a, b) => b.severity_score - a.severity_score);

  return (
    <div className="flex-1 overflow-y-auto p-2 space-y-2">
      <AnimatePresence>
        {sortedIncidents.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex h-full items-center justify-center text-xs text-muted font-mono"
          >
            NO ACTIVE THREATS
          </motion.div>
        ) : (
          sortedIncidents.map((incident) => (
            <motion.div
              key={incident.id}
              layout
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className={`p-3 rounded-md border bg-surface/40 backdrop-blur-sm ${incident.severity === 'CRITICAL' ? 'critical-glow' : ''} border-border/50`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-md border ${getSeverityColor(incident.severity_score)}`}>
                    {getIcon(incident.resolved_type || incident.type)}
                  </div>
                  <span className="font-mono text-sm font-bold text-white">{incident.id}</span>
                </div>
                <div className={`text-[10px] px-2 py-0.5 rounded-full font-mono border ${getSeverityColor(incident.severity_score)}`}>
                  {incident.severity} ({incident.severity_score})
                </div>
              </div>

              <div className="text-sm font-medium text-white mb-1">
                {incident.resolved_type ? incident.resolved_type.replace('_', ' ').toUpperCase() : incident.type.toUpperCase()}
              </div>
              <div className="text-xs text-muted mb-2 line-clamp-2">
                {incident.description}
              </div>

              <div className="flex items-center justify-between text-xs text-muted font-mono">
                <div className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {incident.location.toUpperCase()}
                </div>
                <div className="flex items-center gap-3">
                  {incident.injured_count > 0 && (
                    <span className="flex items-center gap-1 text-red-400">
                      <Users className="w-3 h-3" /> {incident.injured_count}
                    </span>
                  )}
                  {incident.calls_merged > 1 && (
                    <span className="text-primary">{incident.calls_merged} CALLS</span>
                  )}
                </div>
              </div>

              {incident.units && incident.units.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/50 text-[10px] font-mono flex flex-wrap gap-1">
                  <span className="text-muted mr-1">DEPLOYED:</span>
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
