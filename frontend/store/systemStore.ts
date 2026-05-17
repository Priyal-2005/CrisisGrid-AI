import { create } from 'zustand';

// Types
export interface Incident {
  id: string;
  type: string;
  location: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  severity_score: number;
  status: string;
  units: string[];
  time: string;
  description: string;
  calls_merged: number;
  required_resources: Record<string, number>;
  severity_explanation: string;
  zone_risk: {
    chemical_sites?: boolean;
    infrastructure_importance?: number;
    hazard_level?: number;
    population_density?: number;
    description?: string;
  };
}

export interface Resource {
  id: string;
  type: string;
  status: 'AVAILABLE' | 'DISPATCHED' | 'MAINTENANCE';
  location: string;
  eta: number | null;
  assigned_incident: string | null;
  eta_display: string;
}

export interface DispatchEntry {
  time: string;
  incident: string;
  unit: string;
  route: string;
  eta: string;
  severity: string;
  status: string;
  rerouted_from: string;
}

interface Stats {
  total_incidents: number;
  total_dispatches: number;
  units_deployed: number;
  units_total: number;
  utilization: number;
  avg_severity_score: number;
  critical_count: number;
  high_count: number;
}

// Clean initial stats — always start with zeroes, updated by real data
const EMPTY_STATS: Stats = {
  total_incidents: 0,
  total_dispatches: 0,
  units_deployed: 0,
  units_total: 12,
  utilization: 0,
  avg_severity_score: 0,
  critical_count: 0,
  high_count: 0,
};

interface SystemState {
  isConnected: boolean;
  incidents: Incident[];
  resources: Resource[];
  dispatch_log: DispatchEntry[];
  alerts: string[];
  live_feed: string[];
  agent_reasoning: Record<string, string>;
  stats: Stats;
  
  // Actions
  setConnectionStatus: (status: boolean) => void;
  setInitialState: (data: Partial<SystemState>) => void;
  resetState: () => void;
  addIncident: (incident: Incident) => void;
  updateIncident: (incident: Incident) => void;
  updateResources: (resources: Resource[]) => void;
  addDispatch: (entry: DispatchEntry) => void;
  addAlert: (alert: string) => void;
  addFeedEvents: (events: string[]) => void;
  updateReasoning: (reasoning: Record<string, string>) => void;
  updateStats: (stats: Partial<Stats>) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  isConnected: false,
  incidents: [],
  resources: [],
  dispatch_log: [],
  alerts: [],
  live_feed: [],
  agent_reasoning: {},
  stats: { ...EMPTY_STATS },

  setConnectionStatus: (status) => set({ isConnected: status }),
  
  setInitialState: (data) => set((state) => {
    // When receiving state_snapshot from backend, adopt resources and stats
    // but filter incidents/dispatch/reasoning intelligently
    const newState: Partial<SystemState> = {};
    
    // Always adopt resources (shows fleet positions)
    if (data.resources) newState.resources = data.resources;
    
    // Adopt incidents from backend (they're the source of truth)
    if (data.incidents) newState.incidents = data.incidents as Incident[];
    
    // Adopt dispatch log
    if (data.dispatch_log) newState.dispatch_log = data.dispatch_log as DispatchEntry[];
    
    // Adopt stats
    if (data.stats) newState.stats = data.stats as Stats;
    
    // Adopt reasoning
    if (data.agent_reasoning) newState.agent_reasoning = data.agent_reasoning;
    
    // Adopt feed and alerts
    if (data.live_feed) newState.live_feed = data.live_feed;
    if (data.alerts) newState.alerts = data.alerts;
    
    return { ...state, ...newState };
  }),

  // Full state reset — called on system_reset WS event
  resetState: () => set({
    incidents: [],
    resources: [],
    dispatch_log: [],
    alerts: [],
    live_feed: [],
    agent_reasoning: {},
    stats: { ...EMPTY_STATS },
  }),
  
  addIncident: (incident) => set((state) => {
    const existing = state.incidents.find(i => i.id === incident.id);
    const newIncidents = existing
      ? state.incidents.map(i => i.id === incident.id ? incident : i)
      : [incident, ...state.incidents];
    
    // Recompute stats from actual incident data
    const criticalCount = newIncidents.filter(i => i.severity === 'CRITICAL').length;
    const highCount = newIncidents.filter(i => i.severity === 'HIGH').length;
    
    return {
      incidents: newIncidents,
      stats: {
        ...state.stats,
        total_incidents: newIncidents.length,
        critical_count: criticalCount,
        high_count: highCount,
      }
    };
  }),
  
  updateIncident: (incident) => set((state) => ({
    incidents: state.incidents.map(i => i.id === incident.id ? incident : i)
  })),
  
  updateResources: (resources) => set((state) => {
    const dispatched = resources.filter(r => r.status === 'DISPATCHED').length;
    return {
      resources,
      stats: {
        ...state.stats,
        units_deployed: dispatched,
        units_total: resources.length,
        utilization: Math.round((dispatched / Math.max(resources.length, 1)) * 100) / 100,
      }
    };
  }),
  
  addDispatch: (entry) => set((state) => ({
    dispatch_log: [entry, ...state.dispatch_log],
    stats: {
      ...state.stats,
      total_dispatches: state.stats.total_dispatches + 1,
    }
  })),
  
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, 30)
  })),
  
  addFeedEvents: (events) => set((state) => ({
    live_feed: [...events, ...state.live_feed].slice(0, 50)
  })),
  
  updateReasoning: (reasoning) => set((state) => ({
    agent_reasoning: { ...state.agent_reasoning, ...reasoning }
  })),

  updateStats: (partial) => set((state) => ({
    stats: { ...state.stats, ...partial }
  })),
}));
