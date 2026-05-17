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

interface SystemState {
  isConnected: boolean;
  incidents: Incident[];
  resources: Resource[];
  dispatch_log: DispatchEntry[];
  alerts: string[];
  live_feed: string[];
  agent_reasoning: Record<string, string>;
  stats: Stats | null;
  
  // Actions
  setConnectionStatus: (status: boolean) => void;
  setInitialState: (data: Partial<SystemState>) => void;
  addIncident: (incident: Incident) => void;
  updateIncident: (incident: Incident) => void;
  updateResources: (resources: Resource[]) => void;
  addDispatch: (entry: DispatchEntry) => void;
  addAlert: (alert: string) => void;
  addFeedEvents: (events: string[]) => void;
  updateReasoning: (reasoning: Record<string, string>) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  isConnected: false,
  incidents: [],
  resources: [],
  dispatch_log: [],
  alerts: [],
  live_feed: [],
  agent_reasoning: {},
  stats: null,

  setConnectionStatus: (status) => set({ isConnected: status }),
  
  setInitialState: (data) => set((state) => ({ ...state, ...data })),
  
  addIncident: (incident) => set((state) => ({
    incidents: [incident, ...state.incidents.filter(i => i.id !== incident.id)],
    stats: state.stats ? {
      ...state.stats,
      total_incidents: state.stats.total_incidents + 1,
      critical_count: incident.severity === 'CRITICAL' ? state.stats.critical_count + 1 : state.stats.critical_count,
    } : null
  })),
  
  updateIncident: (incident) => set((state) => ({
    incidents: state.incidents.map(i => i.id === incident.id ? incident : i)
  })),
  
  updateResources: (resources) => set({ resources }),
  
  addDispatch: (entry) => set((state) => ({
    dispatch_log: [entry, ...state.dispatch_log]
  })),
  
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts]
  })),
  
  addFeedEvents: (events) => set((state) => ({
    live_feed: [...events, ...state.live_feed].slice(0, 50)
  })),
  
  updateReasoning: (reasoning) => set((state) => ({
    agent_reasoning: { ...state.agent_reasoning, ...reasoning }
  }))
}));
