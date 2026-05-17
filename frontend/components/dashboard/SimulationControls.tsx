"use client";

import { useState } from "react";
import { useSystemStore } from "@/store/systemStore";
import { Play, RotateCcw, Activity, Zap } from "lucide-react";

export function SimulationControls() {
  const [isRunning, setIsRunning] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [statusText, setStatusText] = useState("SYSTEM READY");
  const resetState = useSystemStore((s) => s.resetState);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const runScenario = async () => {
    setIsRunning(true);
    setStatusText("EXECUTING SCENARIO...");
    try {
      const res = await fetch(`${API_URL}/api/v1/simulation/scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delay: 1.5 })
      });
      if (res.ok) {
        setStatusText("SCENARIO COMPLETE");
      } else {
        setStatusText("SCENARIO FAILED");
      }
    } catch (err) {
      setStatusText("CONNECTION ERROR");
    } finally {
      setIsRunning(false);
    }
  };

  const resetSystem = async () => {
    setIsResetting(true);
    setStatusText("RESETTING...");

    // Immediately clear frontend state for instant visual feedback
    resetState();

    try {
      const res = await fetch(`${API_URL}/api/v1/simulation/reset`, {
        method: "POST"
      });
      if (res.ok) {
        setStatusText("SYSTEM READY");
      } else {
        setStatusText("RESET FAILED");
      }
    } catch (err) {
      setStatusText("CONNECTION ERROR");
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="flex-1 p-3 flex flex-col justify-between gap-2">
      <div className={`font-mono text-[10px] px-2 py-1.5 rounded flex items-center gap-1.5 border ${
        isRunning 
          ? 'text-high bg-high/10 border-high/30 animate-pulse' 
          : statusText === 'SYSTEM READY' 
          ? 'text-low bg-low/10 border-low/30'
          : 'text-primary bg-primary/10 border-primary/30'
      }`}>
        {isRunning ? <Zap className="w-3 h-3" /> : <Activity className="w-3 h-3" />}
        {statusText}
      </div>
      
      <div className="flex flex-col gap-2">
        <button 
          onClick={runScenario}
          disabled={isRunning || isResetting}
          className={`flex items-center justify-center gap-1.5 border rounded py-2 font-mono text-[10px] transition-all ${
            isRunning 
              ? "bg-high/30 border-high text-white animate-pulse shadow-[0_0_12px_rgba(255,107,53,0.4)]" 
              : "bg-high/15 hover:bg-high/25 border-high/60 text-high"
          } disabled:opacity-70`}
        >
          <Play className="w-3 h-3" />
          {isRunning ? "SIMULATING..." : "RUN DEMO"}
        </button>
        
        <button 
          onClick={resetSystem}
          disabled={isRunning || isResetting}
          className="flex items-center justify-center gap-1.5 bg-surface hover:bg-surface/80 border border-border text-muted hover:text-white rounded py-2 font-mono text-[10px] transition-colors disabled:opacity-50"
        >
          <RotateCcw className={`w-3 h-3 ${isResetting ? 'animate-spin' : ''}`} />
          {isResetting ? "RESETTING..." : "RESET"}
        </button>
      </div>

      <div className="text-[9px] text-muted/60 font-mono leading-tight">
        Demo triggers 6 sequential 112 calls showcasing merging, escalation &amp; rerouting.
      </div>
    </div>
  );
}
