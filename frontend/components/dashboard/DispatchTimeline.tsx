"use client";

import { useSystemStore } from "@/store/systemStore";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Clock, Navigation, Truck } from "lucide-react";

export function DispatchTimeline() {
  const dispatch_log = useSystemStore((s) => s.dispatch_log);

  return (
    <div className="flex-1 overflow-y-auto p-3 font-mono text-[10px] space-y-2">
      {dispatch_log.length === 0 ? (
        <div className="flex h-full items-center justify-center text-muted text-[10px] flex-col gap-2">
          <Truck className="w-5 h-5 text-border" />
          <span>NO DISPATCHES YET</span>
        </div>
      ) : (
        <AnimatePresence mode="popLayout">
          {dispatch_log.map((entry, i) => {
            const isReroute = entry.status?.includes('REROUTED');
            
            return (
              <motion.div
                key={`${entry.incident}-${entry.unit}-${i}`}
                layout
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
                className={`relative pl-3 border-l-2 ${isReroute ? 'border-critical' : 'border-primary/40'} py-0.5`}
              >
                {/* Timeline dot */}
                <div className={`absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-background border-2 ${isReroute ? 'border-critical' : 'border-primary'}`}></div>
                
                {/* Time + Status */}
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Clock className="w-2.5 h-2.5 text-muted/60" />
                  <span className="text-muted/70 text-[9px]">{entry.time}</span>
                  <span className={`px-1 py-px rounded-sm text-[9px] ${isReroute ? 'bg-critical/15 text-critical' : 'bg-primary/15 text-primary'}`}>
                    {entry.status}
                  </span>
                </div>
                
                {/* Unit → Incident */}
                <div className="text-white/90 text-[10px]">
                  <span className="font-bold text-high">{entry.unit}</span>
                  <span className="text-muted mx-1">→</span>
                  <span className="font-bold text-white">{entry.incident}</span>
                </div>
                
                {/* Route + ETA */}
                <div className="flex items-start gap-1.5 mt-0.5 text-muted/60">
                  <Navigation className="w-2.5 h-2.5 mt-0.5 shrink-0" />
                  <span className="leading-snug text-[9px]">
                    {entry.route}
                    <span className="text-primary/80 ml-1">ETA {entry.eta}</span>
                  </span>
                </div>

                {/* Reroute indicator */}
                {isReroute && entry.rerouted_from && (
                  <div className="flex items-center gap-1 mt-0.5 text-critical text-[9px]">
                    <AlertCircle className="w-2.5 h-2.5" />
                    ⚡ Pulled from {entry.rerouted_from}
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      )}
    </div>
  );
}
