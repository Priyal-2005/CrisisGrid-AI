"use client";

import { useSystemStore } from "@/store/systemStore";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Clock, Navigation } from "lucide-react";

export function DispatchTimeline() {
  const { dispatch_log } = useSystemStore();

  return (
    <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-3">
      {dispatch_log.length === 0 ? (
        <div className="flex h-full items-center justify-center text-muted">
          No dispatches yet.
        </div>
      ) : (
        <AnimatePresence>
          {dispatch_log.map((entry, i) => {
            const isReroute = entry.status.includes('REROUTED');
            
            return (
              <motion.div
                key={`${entry.incident}-${entry.unit}-${entry.time}-${i}`}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`relative pl-4 border-l ${isReroute ? 'border-critical' : 'border-primary/50'}`}
              >
                <div className={`absolute -left-1.5 top-0.5 w-3 h-3 rounded-full bg-background border-2 ${isReroute ? 'border-critical' : 'border-primary'}`}></div>
                
                <div className="flex items-center gap-2 mb-1">
                  <Clock className="w-3 h-3 text-muted" />
                  <span className="text-muted">{entry.time}</span>
                  <span className={`px-1.5 rounded-sm bg-surface ${isReroute ? 'text-critical' : 'text-primary'}`}>
                    {entry.status}
                  </span>
                </div>
                
                <div className="text-white">
                  <span className="font-bold text-high">{entry.unit}</span> dispatched to <span className="font-bold text-white">{entry.incident}</span>
                </div>
                
                <div className="flex items-start gap-2 mt-1 text-muted">
                  <Navigation className="w-3 h-3 mt-0.5" />
                  <div className="flex-1 leading-snug">
                    {entry.route} <span className="text-primary ml-1">(ETA: {entry.eta})</span>
                  </div>
                </div>

                {isReroute && entry.rerouted_from && (
                  <div className="flex items-center gap-1 mt-1 text-critical">
                    <AlertCircle className="w-3 h-3" />
                    Pulled from {entry.rerouted_from}
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
