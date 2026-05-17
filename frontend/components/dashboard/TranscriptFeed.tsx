"use client";

import { useSystemStore } from "@/store/systemStore";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, PhoneCall } from "lucide-react";

export function TranscriptFeed() {
  const live_feed = useSystemStore((s) => s.live_feed);

  // Filter to call-related events
  const transcripts = live_feed.filter(feed => feed.includes('📞') || feed.includes('Call'));

  return (
    <div className="flex-1 overflow-y-auto p-3 font-mono text-[10px] space-y-2">
      {transcripts.length === 0 ? (
        <div className="flex h-full items-center justify-center text-muted text-[10px] flex-col gap-2">
          <Mic className="w-5 h-5 text-border" />
          <span>AWAITING 112 SIGNALS</span>
        </div>
      ) : (
        <AnimatePresence mode="popLayout">
          {transcripts.map((entry, i) => (
            <motion.div
              key={`transcript-${i}-${entry.substring(0, 12)}`}
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="relative pl-3 border-l-2 border-primary/30 py-0.5"
            >
              <div className="absolute -left-[5px] top-1.5 w-2 h-2 rounded-full bg-background border-2 border-primary animate-pulse"></div>
              
              <div className="flex items-center gap-1.5 mb-0.5">
                <PhoneCall className="w-2.5 h-2.5 text-primary" />
                <span className="text-primary font-bold text-[9px]">112 TRANSCRIPT</span>
              </div>
              
              <div className="text-white/80 italic leading-snug text-[10px]">
                &ldquo;{entry.replace('📞 Call:', '').replace('📞', '').trim()}&rdquo;
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      )}
    </div>
  );
}
