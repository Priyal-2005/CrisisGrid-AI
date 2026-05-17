"use client";

import { useSystemStore } from "@/store/systemStore";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, PhoneCall } from "lucide-react";

export function TranscriptFeed() {
  const { live_feed } = useSystemStore();

  // Filter out the raw calls if we have specific formatting or just use all feed events
  // The backend emits calls with a 📞 emoji typically. Let's capture those.
  const transcripts = live_feed.filter(feed => feed.includes('📞') || feed.includes('Call'));

  return (
    <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-3">
      {transcripts.length === 0 ? (
        <div className="flex h-full items-center justify-center text-muted flex-col gap-2">
          <Mic className="w-5 h-5 text-border" />
          <span>Awaiting emergency signals...</span>
        </div>
      ) : (
        <AnimatePresence>
          {transcripts.map((entry, i) => (
            <motion.div
              key={`transcript-${i}-${entry.substring(0, 10)}`}
              initial={{ opacity: 0, x: -20, backgroundColor: "rgba(0, 212, 255, 0.2)" }}
              animate={{ opacity: 1, x: 0, backgroundColor: "rgba(0,0,0,0)" }}
              className="relative pl-4 border-l border-primary/50 py-1"
            >
              <div className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-background border-2 border-primary animate-pulse"></div>
              
              <div className="flex items-center gap-2 mb-1">
                <PhoneCall className="w-3 h-3 text-primary" />
                <span className="text-primary font-bold">INCOMING 112 TRANSCRIPT</span>
              </div>
              
              <div className="text-white/90 italic leading-relaxed">
                "{entry.replace('📞 Call:', '').replace('📞', '').trim()}"
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      )}
    </div>
  );
}
