"use client";

import { useSystemStore } from "@/store/systemStore";
import { useEffect, useRef } from "react";
import { BrainCircuit, Filter, Navigation, Route } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function ReasoningPanel() {
  const { agent_reasoning } = useSystemStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agent_reasoning]);

  const agents = [
    { name: "Triage Agent", icon: <Filter className="w-4 h-4 text-primary" /> },
    { name: "Fusion Agent", icon: <BrainCircuit className="w-4 h-4 text-purple-400" /> },
    { name: "Dispatch Agent", icon: <Navigation className="w-4 h-4 text-high" /> },
    { name: "Strategy Agent", icon: <Route className="w-4 h-4 text-emerald-400" /> },
  ];

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-[11px]"
    >
      {Object.keys(agent_reasoning).length === 0 ? (
        <div className="flex h-full items-center justify-center text-muted">
          Awaiting LLM response...
        </div>
      ) : (
        <AnimatePresence>
          {agents.map((agent) => {
            const reasoning = agent_reasoning[agent.name];
            if (!reasoning) return null;

            return (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 bg-surface/40 border border-border/50 rounded-lg p-3 shadow-lg"
              >
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border/50">
                  {agent.icon}
                  <span className="font-bold tracking-wider text-white/90 text-[10px]">{agent.name.toUpperCase()}</span>
                </div>
                <div className="text-muted whitespace-pre-wrap leading-relaxed text-[11px] font-mono">
                  {reasoning}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      )}
    </div>
  );
}
