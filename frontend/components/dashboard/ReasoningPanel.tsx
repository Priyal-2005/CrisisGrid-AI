"use client";

import { useSystemStore } from "@/store/systemStore";
import { useEffect, useRef } from "react";
import { BrainCircuit, Filter, Navigation, Route } from "lucide-react";

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
        agents.map((agent) => {
          const reasoning = agent_reasoning[agent.name];
          if (!reasoning) return null;

          return (
            <div key={agent.name} className="space-y-2">
              <div className="flex items-center gap-2 text-white/80">
                {agent.icon}
                <span className="font-semibold">{agent.name.toUpperCase()}</span>
              </div>
              <div className="pl-6 text-muted border-l border-border/50 whitespace-pre-wrap leading-relaxed">
                {reasoning}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
