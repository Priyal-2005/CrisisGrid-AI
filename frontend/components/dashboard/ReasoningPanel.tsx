"use client";

import { useSystemStore } from "@/store/systemStore";
import { useRef, useState } from "react";
import { BrainCircuit, Filter, Navigation, Route, ChevronDown, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const AGENTS = [
  { key: "Triage Agent", icon: Filter, color: "text-primary", label: "TRIAGE" },
  { key: "Fusion Agent", icon: BrainCircuit, color: "text-purple-400", label: "FUSION" },
  { key: "Dispatch Agent", icon: Navigation, color: "text-high", label: "DISPATCH" },
  { key: "Strategy Agent", icon: Route, color: "text-emerald-400", label: "STRATEGY" },
];

// Truncate verbose reasoning to first N characters, with expand toggle
function ReasoningBlock({ label, reasoning, icon: Icon, color }: {
  label: string;
  reasoning: string;
  icon: any;
  color: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const isLong = reasoning.length > 200;
  const display = expanded || !isLong ? reasoning : reasoning.substring(0, 200) + "...";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="bg-surface/30 border border-border/30 rounded-md overflow-hidden"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center gap-2 hover:bg-surface/50 transition-colors"
      >
        <Icon className={`w-3.5 h-3.5 ${color}`} />
        <span className="font-bold tracking-wider text-white/80 text-[10px] flex-1 text-left">{label}</span>
        {isLong && (
          expanded
            ? <ChevronDown className="w-3 h-3 text-muted" />
            : <ChevronRight className="w-3 h-3 text-muted" />
        )}
      </button>
      <div className="px-3 pb-2 text-muted text-[10px] leading-relaxed font-mono whitespace-pre-wrap break-words">
        {display}
      </div>
    </motion.div>
  );
}

export function ReasoningPanel() {
  const agent_reasoning = useSystemStore((s) => s.agent_reasoning);
  const scrollRef = useRef<HTMLDivElement>(null);

  const hasReasoning = Object.keys(agent_reasoning).length > 0;

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-[11px]"
    >
      {!hasReasoning ? (
        <div className="flex h-full items-center justify-center text-muted text-[10px] flex-col gap-2">
          <BrainCircuit className="w-5 h-5 text-border" />
          <span>Awaiting AI pipeline...</span>
        </div>
      ) : (
        <AnimatePresence>
          {AGENTS.map((agent) => {
            const reasoning = agent_reasoning[agent.key];
            if (!reasoning) return null;

            return (
              <ReasoningBlock
                key={agent.key}
                label={agent.label}
                reasoning={reasoning}
                icon={agent.icon}
                color={agent.color}
              />
            );
          })}
        </AnimatePresence>
      )}
    </div>
  );
}
