"use client";

import { useWebSocket } from "@/hooks/useWebSocket";
import { useSystemStore } from "@/store/systemStore";
import { useEffect } from "react";
import { Activity, AlertTriangle, CheckCircle2, ShieldAlert, PhoneCall } from "lucide-react";

import { TranscriptFeed } from "@/components/dashboard/TranscriptFeed";
import { IncidentFeed } from "@/components/dashboard/IncidentFeed";
import { DispatchTimeline } from "@/components/dashboard/DispatchTimeline";
import { ReasoningPanel } from "@/components/dashboard/ReasoningPanel";
import { SimulationControls } from "@/components/dashboard/SimulationControls";
import { TranscriptInput } from "@/components/dashboard/TranscriptInput";
import dynamic from 'next/dynamic';

const MapPanel = dynamic(
  () => import("@/components/dashboard/MapPanel").then(mod => mod.MapPanel),
  { ssr: false, loading: () => <div className="absolute inset-0 flex items-center justify-center text-xs text-muted font-mono">LOADING MAP ENGINE...</div> }
);

export default function DashboardPage() {
  // Initialize websocket connection
  useWebSocket();
  const { isConnected, stats, alerts, live_feed } = useSystemStore();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Navbar */}
      <header className="h-14 border-b border-border bg-surface/50 backdrop-blur-md flex items-center justify-between px-6 shrink-0 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-primary" />
            <h1 className="font-mono font-bold tracking-tight text-white">CRISISGRID<span className="text-primary">.AI</span></h1>
          </div>
          <div className="h-4 w-[1px] bg-border mx-2"></div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-low shadow-[0_0_8px_rgba(48,209,88,0.5)]' : 'bg-critical shadow-[0_0_8px_rgba(255,45,85,0.5)]'} animate-pulse`}></div>
            <span className={isConnected ? 'text-low' : 'text-critical'}>
              {isConnected ? 'LIVE / CONNECTED' : 'DISCONNECTED / RETRYING'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex gap-4 text-xs font-mono">
            <div className="flex flex-col items-end">
              <span className="text-muted">ACTIVE INCIDENTS</span>
              <span className="text-white font-bold">{stats?.total_incidents || 0}</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-muted">CRITICAL RISK</span>
              <span className="text-critical font-bold">{stats?.critical_count || 0}</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-muted">FLEET DEPLOYED</span>
              <span className="text-high font-bold">{stats?.units_deployed || 0}/{stats?.units_total || 0} ({(stats?.utilization || 0) * 100}%)</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 p-4 grid grid-cols-12 gap-4 h-[calc(100vh-3.5rem)] overflow-hidden">

        {/* Left Column: Incidents & Alerts */}
        <div className="col-span-3 flex flex-col gap-4 overflow-hidden">

          {/* Transcript Feed */}
          <div className="glass-panel rounded-lg h-1/3 overflow-hidden flex flex-col">
            <div className="p-3 border-b border-border/50 flex items-center justify-between bg-surface/30">
              <h2 className="text-xs font-mono text-muted flex items-center gap-2">
                <PhoneCall className="w-3.5 h-3.5" />
                LIVE CALL FEED
              </h2>
            </div>
            <TranscriptFeed />
          </div>

          <div className="glass-panel rounded-lg flex-1 overflow-hidden flex flex-col">
            <div className="p-3 border-b border-border/50 flex items-center justify-between bg-surface/30">
              <h2 className="text-xs font-mono text-muted flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5" />
                ACTIVE THREATS
              </h2>
            </div>
            <IncidentFeed />
          </div>
        </div>

        {/* Center Column: Map & Simulation */}
        <div className="col-span-6 flex flex-col gap-4 overflow-hidden">
          <div className="glass-panel rounded-lg flex-1 overflow-hidden relative">
            <MapPanel />
          </div>

          <div className="h-56 flex gap-4 shrink-0">
            <div className="glass-panel rounded-lg flex-1 overflow-hidden flex flex-col">
              <div className="p-3 border-b border-border/50 bg-surface/30">
                <h2 className="text-xs font-mono text-muted">MANUAL OVERRIDE / TRANSCRIPT INPUT</h2>
              </div>
              <TranscriptInput />
            </div>

            <div className="glass-panel rounded-lg w-1/3 overflow-hidden flex flex-col">
              <div className="p-3 border-b border-border/50 bg-surface/30">
                <h2 className="text-xs font-mono text-muted">SIMULATION CONTROLS</h2>
              </div>
              <SimulationControls />
            </div>
          </div>
        </div>

        {/* Right Column: Reasoning & Dispatch */}
        <div className="col-span-3 flex flex-col gap-4 overflow-hidden">
          <div className="glass-panel rounded-lg h-1/2 overflow-hidden flex flex-col">
            <div className="p-3 border-b border-border/50 bg-surface/30 flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-low" />
              <h2 className="text-xs font-mono text-muted">DISPATCH TIMELINE</h2>
            </div>
            <DispatchTimeline />
          </div>

          <div className="glass-panel rounded-lg h-1/2 overflow-hidden flex flex-col">
            <div className="p-3 border-b border-border/50 bg-surface/30 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-primary" />
              <h2 className="text-xs font-mono text-muted">AI REASONING CORE</h2>
            </div>
            <ReasoningPanel />
          </div>
        </div>

      </main>
    </div>
  );
}
