"use client";

import { useState } from "react";
import { Play, RotateCcw, Activity } from "lucide-react";

export function SimulationControls() {
  const [isRunning, setIsRunning] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [statusText, setStatusText] = useState("SYSTEM READY");

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const runScenario = async () => {
    setIsRunning(true);
    setStatusText("EXECUTING TEST SCENARIO...");
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
    setStatusText("RESETTING SYSTEM STATE...");
    try {
      const res = await fetch(`${API_URL}/api/v1/simulation/reset`, {
        method: "POST"
      });
      if (res.ok) {
        setStatusText("SYSTEM RESET SUCCESSFUL");
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
    <div className="flex-1 p-4 flex flex-col justify-between">
      <div className="font-mono text-[10px] text-primary bg-primary/10 border border-primary/30 p-2 rounded flex items-center gap-2">
        <Activity className="w-3 h-3 animate-pulse" />
        {statusText}
      </div>
      
      <div className="grid grid-cols-2 gap-3 mt-4">
        <button 
          onClick={runScenario}
          disabled={isRunning || isResetting}
          className={`flex items-center justify-center gap-2 border rounded-md py-3 font-mono text-xs transition-all ${
            isRunning ? "bg-high/40 border-high text-white animate-pulse shadow-[0_0_15px_rgba(255,107,53,0.5)]" : "bg-high/20 hover:bg-high/30 border-high text-high"
          } disabled:opacity-80`}
        >
          <Play className="w-4 h-4" />
          {isRunning ? "SIMULATING INCIDENTS..." : "RUN DEMO SCENARIO"}
        </button>
        
        <button 
          onClick={resetSystem}
          disabled={isRunning || isResetting}
          className="flex items-center justify-center gap-2 bg-surface hover:bg-surface/80 border border-border text-white rounded-md py-3 font-mono text-xs transition-colors disabled:opacity-50"
        >
          <RotateCcw className="w-4 h-4 text-muted" />
          {isResetting ? "RESETTING..." : "RESET STATE"}
        </button>
      </div>

      <div className="mt-3 text-[10px] text-muted font-mono leading-tight">
        * Running the scenario will sequentially trigger 6 complex 112 calls to demonstrate the AI's merging, escalation, and strategic rerouting capabilities.
      </div>
    </div>
  );
}
