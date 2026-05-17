"use client";

import { useWebSocket } from "@/hooks/useWebSocket";
import { useSystemStore } from "@/store/systemStore";
import { Activity, AlertTriangle, CheckCircle2, ShieldAlert, PhoneCall, Radio } from "lucide-react";

import { TranscriptFeed } from "@/components/dashboard/TranscriptFeed";
import { IncidentFeed } from "@/components/dashboard/IncidentFeed";
import { DispatchTimeline } from "@/components/dashboard/DispatchTimeline";
import { ReasoningPanel } from "@/components/dashboard/ReasoningPanel";
import { SimulationControls } from "@/components/dashboard/SimulationControls";
import { TranscriptInput } from "@/components/dashboard/TranscriptInput";
import dynamic from 'next/dynamic';

const MapPanel = dynamic(
  () => import("@/components/dashboard/MapPanel").then(mod => mod.MapPanel),
  { ssr: false, loading: () => <div className="absolute inset-0 flex items-center justify-center text-xs text-muted font-mono">INITIALIZING MAP ENGINE...</div> }
);

export default function DashboardPage() {
  // Initialize websocket connection
  useWebSocket();
  const { isConnected, stats } = useSystemStore();

  const utilPct = Math.round((stats.utilization || 0) * 100);

  return (
    <div className="h-screen bg-background text-foreground flex flex-col overflow-hidden">
      {/* ═══════ Top Command Bar ═══════ */}
      <header className="h-12 border-b border-border/60 bg-surface/60 backdrop-blur-xl flex items-center justify-between px-5 shrink-0 z-50">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4.5 h-4.5 text-primary" />
            <h1 className="font-mono font-bold tracking-tight text-sm text-white">CRISISGRID<span className="text-primary">.AI</span></h1>
          </div>
          <div className="h-4 w-px bg-border/50 mx-1"></div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-low shadow-[0_0_6px_rgba(48,209,88,0.6)]' : 'bg-critical shadow-[0_0_6px_rgba(255,45,85,0.6)]'} animate-pulse`}></div>
            <span className={isConnected ? 'text-low' : 'text-critical'}>
              {isConnected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Stats Strip */}
        <div className="flex items-center gap-5 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-muted">INCIDENTS</span>
            <span className="text-white font-bold tabular-nums">{stats.total_incidents}</span>
          </div>
          <div className="w-px h-3 bg-border/40"></div>
          <div className="flex items-center gap-1.5">
            <span className="text-muted">CRITICAL</span>
            <span className={`font-bold tabular-nums ${stats.critical_count > 0 ? 'text-critical' : 'text-muted'}`}>{stats.critical_count}</span>
          </div>
          <div className="w-px h-3 bg-border/40"></div>
          <div className="flex items-center gap-1.5">
            <span className="text-muted">FLEET</span>
            <span className="text-high font-bold tabular-nums">{stats.units_deployed}/{stats.units_total}</span>
            <span className={`px-1 py-px rounded text-[9px] ${
              utilPct >= 75 ? 'bg-critical/20 text-critical' : utilPct >= 50 ? 'bg-high/20 text-high' : 'bg-low/20 text-low'
            }`}>{utilPct}%</span>
          </div>
        </div>
      </header>

      {/* ═══════ Main Dashboard Grid ═══════ */}
      <main className="flex-1 p-3 grid grid-cols-12 gap-3 min-h-0 overflow-hidden">

        {/* ─── LEFT: Situational Awareness ─── */}
        <div className="col-span-3 flex flex-col gap-3 min-h-0">

          {/* ACTIVE THREATS — Primary situational panel, top position */}
          <div className="glass-panel rounded-lg flex-[3] min-h-0 overflow-hidden flex flex-col">
            <div className="px-3 py-2.5 border-b border-border/40 flex items-center gap-2 bg-surface/30 shrink-0">
              <AlertTriangle className="w-3.5 h-3.5 text-critical" />
              <h2 className="text-[10px] font-mono text-muted tracking-wider">ACTIVE THREATS</h2>
              <span className="ml-auto text-[9px] font-mono text-critical tabular-nums">{stats.total_incidents > 0 ? `${stats.total_incidents} ACTIVE` : ''}</span>
            </div>
            <IncidentFeed />
          </div>

          {/* LIVE CALL FEED — Secondary, below threats */}
          <div className="glass-panel rounded-lg flex-[2] min-h-0 overflow-hidden flex flex-col">
            <div className="px-3 py-2.5 border-b border-border/40 flex items-center gap-2 bg-surface/30 shrink-0">
              <PhoneCall className="w-3.5 h-3.5 text-primary" />
              <h2 className="text-[10px] font-mono text-muted tracking-wider">LIVE CALL FEED</h2>
            </div>
            <TranscriptFeed />
          </div>
        </div>

        {/* ─── CENTER: Tactical Map + Input ─── */}
        <div className="col-span-6 flex flex-col gap-3 min-h-0">
          {/* Map — occupies most of the center */}
          <div className="glass-panel rounded-lg flex-1 min-h-0 overflow-hidden relative">
            <MapPanel />
          </div>

          {/* Controls Strip — compact row below map */}
          <div className="flex gap-3 shrink-0" style={{ height: '200px' }}>
            <div className="glass-panel rounded-lg flex-1 overflow-hidden flex flex-col">
              <div className="px-3 py-2 border-b border-border/40 bg-surface/30 shrink-0 flex items-center gap-2">
                <Radio className="w-3.5 h-3.5 text-primary" />
                <h2 className="text-[10px] font-mono text-muted tracking-wider">TRANSCRIPT INPUT</h2>
              </div>
              <TranscriptInput />
            </div>

            <div className="glass-panel rounded-lg overflow-hidden flex flex-col" style={{ width: '240px' }}>
              <div className="px-3 py-2 border-b border-border/40 bg-surface/30 shrink-0">
                <h2 className="text-[10px] font-mono text-muted tracking-wider">SIMULATION</h2>
              </div>
              <SimulationControls />
            </div>
          </div>
        </div>

        {/* ─── RIGHT: Dispatch + Intelligence ─── */}
        <div className="col-span-3 flex flex-col gap-3 min-h-0">
          {/* DISPATCH TIMELINE — Primary operational feed */}
          <div className="glass-panel rounded-lg flex-1 min-h-0 overflow-hidden flex flex-col">
            <div className="px-3 py-2.5 border-b border-border/40 bg-surface/30 flex items-center gap-2 shrink-0">
              <CheckCircle2 className="w-3.5 h-3.5 text-low" />
              <h2 className="text-[10px] font-mono text-muted tracking-wider">DISPATCH TIMELINE</h2>
              <span className="ml-auto text-[9px] font-mono text-low tabular-nums">{stats.total_dispatches > 0 ? `${stats.total_dispatches} OPS` : ''}</span>
            </div>
            <DispatchTimeline />
          </div>

          {/* AI REASONING — Secondary intelligence feed */}
          <div className="glass-panel rounded-lg flex-1 min-h-0 overflow-hidden flex flex-col">
            <div className="px-3 py-2.5 border-b border-border/40 bg-surface/30 flex items-center gap-2 shrink-0">
              <Activity className="w-3.5 h-3.5 text-primary" />
              <h2 className="text-[10px] font-mono text-muted tracking-wider">AI REASONING CORE</h2>
            </div>
            <ReasoningPanel />
          </div>
        </div>

      </main>
    </div>
  );
}
