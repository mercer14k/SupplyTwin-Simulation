export interface Provenance {
  id: string;
  source_id: string;
  ingested_at: string;
  validation_status: string;
  lineage: Record<string, string>;
}
export interface Node extends Provenance {
  name: string;
  kind: "supplier" | "plant" | "dc" | "customer";
  latitude: number;
  longitude: number;
  capacity: number;
  coverage_days: number;
  safety_days: number;
  initial_days: number;
  process_cost: number;
}
export interface Lane extends Provenance {
  source: string;
  target: string;
  lead_time: number;
  capacity: number;
  unit_cost: number;
  allocation: number;
}
export interface SKU extends Provenance {
  name: string;
  unit_cost: number;
  holding_cost: number;
  backlog_cost: number;
}
export interface Network extends Provenance {
  nodes: Node[];
  lanes: Lane[];
  skus: SKU[];
  demand: { id: string; customer: string; sku: string; daily_mean: number }[];
}
export interface Scenario extends Provenance {
  name: string;
  description: string;
  version: number;
  parent_id: string | null;
  horizon: number;
  seed: number;
  start_day: number;
  end_day: number;
  demand_multiplier: number;
  capacity_multipliers: Record<string, number>;
  lane_capacity_multipliers: Record<string, number>;
  lead_time_overrides: Record<string, number>;
  sourcing_weights: Record<string, number>;
  safety_stock_multiplier: number;
}
export interface Day {
  day: number;
  demand: number;
  dispatched: number;
  backlog: number;
  inventory: number;
  in_transit: number;
  delivered: number;
  sourced: number;
  total_demand: number;
  total_dispatch: number;
  modeled_cost: number;
  mass_error: number;
  demand_error: number;
  fill_rate: number;
}
export interface NodeDay {
  day: number;
  node_id: string;
  inventory: number;
  in_transit: number;
  used_capacity: number;
  available_capacity: number;
  utilization: number;
}
export interface Result {
  network_id: string;
  result_hash: string;
  engine_version: string;
  network_hash: string;
  seed: number;
  horizon: number;
  scenario: Scenario;
  kpis: Record<string, number>;
  daily: Day[];
  node_daily: NodeDay[];
  flows: { day: number; lane_id: string; units: number }[];
  skus: {
    sku_id: string;
    demand: number;
    dispatched: number;
    backlog: number;
    inventory: number;
  }[];
  invariants: {
    max_mass_error: number;
    max_demand_error: number;
    passed: boolean;
  };
  cost_breakdown: Record<string, number>;
}
export interface Evidence {
  id: string;
  metric: string;
  baseline: number;
  scenario: number;
  delta: number;
  source: string;
}
export interface Run {
  id: string;
  created_at: string;
  baseline: Result;
  scenario: Result;
  deltas: Record<string, number>;
  evidence: Evidence[];
}
export interface Explanation {
  status: string;
  origin: string;
  reason: string;
  claims: (Evidence & { text: string; direction: string })[];
  telemetry: Record<string, unknown>;
}
export interface Report {
  accepted: boolean;
  issues: { path: string; severity: string; message: string }[];
  record_count: number;
}
