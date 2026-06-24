// Typed client for the Sentinel backend.
// BACKEND_URL is read server-side; the browser uses NEXT_PUBLIC_BACKEND_URL.

export interface DependencyStatus {
  name: string;
  healthy: boolean;
  detail: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  dependencies: DependencyStatus[];
}

export interface EcsEvent {
  "@timestamp": string;
  event_action?: string;
  event_category?: string;
  event_severity?: number;
  event_outcome?: string;
  host_name?: string;
  source_ip?: string;
  user_name?: string;
  message?: string;
  [key: string]: unknown;
}

export interface EventsResponse {
  count: number;
  events: EcsEvent[];
}

export interface EventFilters {
  host_name?: string;
  source_ip?: string;
  user_name?: string;
  event_category?: string;
  min_severity?: number;
  message?: string;
  limit?: number;
}

const SERVER_BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// Browser-reachable base (proxied or public). Falls back to localhost in dev.
export const PUBLIC_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${SERVER_BACKEND_URL}/healthz`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend /healthz returned ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}

export function buildEventsQuery(filters: EventFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  return params.toString();
}

export async function fetchEvents(filters: EventFilters): Promise<EventsResponse> {
  const qs = buildEventsQuery(filters);
  const res = await fetch(`${PUBLIC_BACKEND_URL}/events?${qs}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend /events returned ${res.status}`);
  }
  return (await res.json()) as EventsResponse;
}

// ============================================================================
// Phase 2: Alerts and Incidents Types
// ============================================================================

export interface Entity {
  type: string;
  value: string;
}

export interface MitreMapping {
  tactic: string;
  technique_id: string;
  technique_name: string;
}

export interface AlertResponse {
  id: number;
  rule_id: string;
  rule_name: string;
  severity: string;
  status: string; // open, acknowledged, resolved, false_positive
  timestamp: string;
  dedup_key: string;
  entities: Entity[];
  mitre_mapping: MitreMapping[];
  sample_events: Record<string, unknown>[];
  incident_id: number | null;
  assignee: string | null;
}

export interface IncidentResponse {
  id: number;
  title: string;
  description: string;
  severity: string;
  status: string; // open, investigating, resolved, closed
  first_seen: string;
  last_seen: string;
  entities: Entity[];
  assignee: string | null;
}

export interface IncidentDetailResponse extends IncidentResponse {
  alerts: AlertResponse[];
}

export interface AlertFilters {
  status?: string;
  severity?: string;
  rule_id?: string;
  limit?: number;
  offset?: number;
}

export interface IncidentFilters {
  status?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}

// ============================================================================
// Phase 2: Alerts and Incidents Client Functions
// ============================================================================

export async function fetchAlerts(filters: AlertFilters = {}): Promise<AlertResponse[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/alerts?${qs}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend /api/alerts returned ${res.status}`);
  }
  return (await res.json()) as AlertResponse[];
}

export async function updateAlert(
  id: number,
  payload: { status?: string; assignee?: string | null; incident_id?: number | null }
): Promise<AlertResponse> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/alerts/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend PATCH /api/alerts/${id} returned ${res.status}`);
  }
  return (await res.json()) as AlertResponse;
}

export async function fetchIncidents(filters: IncidentFilters = {}): Promise<IncidentResponse[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/incidents?${qs}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend /api/incidents returned ${res.status}`);
  }
  return (await res.json()) as IncidentResponse[];
}

export async function fetchIncidentDetail(id: number): Promise<IncidentDetailResponse> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/incidents/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend /api/incidents/${id} returned ${res.status}`);
  }
  return (await res.json()) as IncidentDetailResponse;
}

export async function updateIncident(
  id: number,
  payload: { status?: string; assignee?: string | null; severity?: string; title?: string; description?: string }
): Promise<IncidentResponse> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/incidents/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend PATCH /api/incidents/${id} returned ${res.status}`);
  }
  return (await res.json()) as IncidentResponse;
}

// ============================================================================
// Phase 3: Alerting, Routing, and Silences Client Functions & Types
// ============================================================================

export interface Channel {
  id: number;
  name: string;
  type: string;
  config: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoutingRule {
  id: number;
  name: string;
  criteria: Record<string, any>;
  channel_id: number;
  is_active: boolean;
  escalation_delay_min: number | null;
  channel?: Channel;
}

export interface Silence {
  id: number;
  name: string | null;
  filters: Record<string, any>;
  start_time: string;
  end_time: string;
  is_active: boolean;
}

export async function fetchChannels(): Promise<Channel[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/channels`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend GET /api/channels returned ${res.status}`);
  }
  return (await res.json()) as Channel[];
}

export async function createChannel(payload: Omit<Channel, "id" | "created_at" | "updated_at">): Promise<Channel> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/channels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend POST /api/channels returned ${res.status}`);
  }
  return (await res.json()) as Channel;
}

export async function updateChannel(id: number, payload: Partial<Channel>): Promise<Channel> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/channels/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend PATCH /api/channels/${id} returned ${res.status}`);
  }
  return (await res.json()) as Channel;
}

export async function deleteChannel(id: number): Promise<void> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/channels/${id}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`backend DELETE /api/channels/${id} returned ${res.status}`);
  }
}

export async function testChannel(id: number): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/channels/${id}/test`, { method: "POST" });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(errorBody.detail || `backend POST /api/channels/${id}/test returned ${res.status}`);
  }
  return (await res.json()) as { success: boolean; message: string };
}

export async function fetchRoutingRules(): Promise<RoutingRule[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/routing_rules`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend GET /api/routing_rules returned ${res.status}`);
  }
  return (await res.json()) as RoutingRule[];
}

export async function createRoutingRule(payload: Omit<RoutingRule, "id" | "channel">): Promise<RoutingRule> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/routing_rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend POST /api/routing_rules returned ${res.status}`);
  }
  return (await res.json()) as RoutingRule;
}

export async function updateRoutingRule(id: number, payload: Partial<RoutingRule>): Promise<RoutingRule> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/routing_rules/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend PATCH /api/routing_rules/${id} returned ${res.status}`);
  }
  return (await res.json()) as RoutingRule;
}

export async function deleteRoutingRule(id: number): Promise<void> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/routing_rules/${id}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`backend DELETE /api/routing_rules/${id} returned ${res.status}`);
  }
}

export async function fetchSilences(): Promise<Silence[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/silences`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`backend GET /api/silences returned ${res.status}`);
  }
  return (await res.json()) as Silence[];
}

export async function createSilence(payload: Omit<Silence, "id">): Promise<Silence> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/silences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend POST /api/silences returned ${res.status}`);
  }
  return (await res.json()) as Silence;
}

export async function updateSilence(id: number, payload: Partial<Silence>): Promise<Silence> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/silences/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`backend PATCH /api/silences/${id} returned ${res.status}`);
  }
  return (await res.json()) as Silence;
}

export async function deleteSilence(id: number): Promise<void> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/silences/${id}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`backend DELETE /api/silences/${id} returned ${res.status}`);
  }
}


// ============================================================================
// Phase 4: AI Gateway — triage, NL->SQL, usage
// ============================================================================

export interface MitreTriage {
  tactic?: string;
  technique_id: string;
  technique_name?: string;
}

export interface AlertTriage {
  summary: string;
  severity_assessment: "info" | "low" | "medium" | "high" | "critical";
  false_positive_likelihood: number;
  likely_root_cause?: string;
  affected_assets?: string[];
  mitre_mapping?: MitreTriage[];
  remediation_steps: string[];
  recommended_actions?: string[];
  confidence: number;
}

export interface Nl2SqlResult {
  sql: string;
}

export interface SqlRunResult {
  sql: string;
  columns: string[];
  rows: unknown[][];
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `status ${res.status}` }));
    throw new Error(detail.detail || `request to ${path} failed (${res.status})`);
  }
  return (await res.json()) as T;
}

export function triageAlert(alertId: number): Promise<AlertTriage> {
  return postJson<AlertTriage>(`/api/ai/triage/${alertId}`);
}

export function generateSql(question: string): Promise<Nl2SqlResult> {
  return postJson<Nl2SqlResult>(`/api/ai/nl2sql`, { question });
}

export function runApprovedSql(sql: string): Promise<SqlRunResult> {
  return postJson<SqlRunResult>(`/api/ai/nl2sql/run`, { sql });
}

// ============================================================================
// Phase 5: Connectors (Wazuh / Prometheus / webhook-IN)
// ============================================================================

export interface Connector {
  id: number;
  name: string;
  type: string; // wazuh, prometheus, webhook
  config: Record<string, unknown>;
  is_active: boolean;
  cursor: string | null;
  status: string; // idle, running, error
  last_error: string | null;
  last_run_at: string | null;
}

export async function fetchConnectors(): Promise<Connector[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/connectors`, { cache: "no-store" });
  if (!res.ok) throw new Error(`backend GET /api/connectors returned ${res.status}`);
  return (await res.json()) as Connector[];
}

export function createConnector(
  payload: Pick<Connector, "name" | "type" | "config" | "is_active">,
): Promise<Connector> {
  return postJson<Connector>(`/api/connectors`, payload);
}

export async function updateConnector(
  id: number,
  payload: Partial<Pick<Connector, "name" | "config" | "is_active">>,
): Promise<Connector> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/connectors/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`backend PATCH /api/connectors/${id} returned ${res.status}`);
  return (await res.json()) as Connector;
}

export async function deleteConnector(id: number): Promise<void> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/connectors/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`backend DELETE /api/connectors/${id} returned ${res.status}`);
}

// ============================================================================
// Phase 6: SOAR Playbooks
// ============================================================================

export interface PlaybookNode {
  id: string;
  action: string;
  params: Record<string, unknown>;
}

export interface Playbook {
  id: number;
  name: string;
  trigger_type: string; // alert, incident, cron, webhook
  trigger_filter: Record<string, unknown>;
  nodes: PlaybookNode[];
  edges: string[][];
  auto_approve: boolean;
  is_active: boolean;
}

export interface PlaybookRun {
  id: number;
  playbook_id: number;
  status: string;
  dry_run: boolean;
  node_results: Record<string, unknown>[];
  node_count: number;
}

export async function fetchPlaybooks(): Promise<Playbook[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/playbooks`, { cache: "no-store" });
  if (!res.ok) throw new Error(`backend GET /api/playbooks returned ${res.status}`);
  return (await res.json()) as Playbook[];
}

export function createPlaybook(
  payload: Omit<Playbook, "id">,
): Promise<Playbook> {
  return postJson<Playbook>(`/api/playbooks`, payload);
}

export async function deletePlaybook(id: number): Promise<void> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/playbooks/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`backend DELETE /api/playbooks/${id} returned ${res.status}`);
}

export function dryRunPlaybook(id: number): Promise<PlaybookRun> {
  return postJson<PlaybookRun>(`/api/playbooks/${id}/dry-run`, { trigger: {} });
}

export function runPlaybook(id: number, confirmDangerous = false): Promise<PlaybookRun> {
  return postJson<PlaybookRun>(`/api/playbooks/${id}/run`, {
    trigger: {},
    confirm_dangerous: confirmDangerous,
  });
}

// ============================================================================
// Phase 7: Posture, Benchmark, Dashboard, Audit
// ============================================================================

export interface PostureRun {
  id: number;
  ts: string;
  tool: string;
  score: number;
  drift: number;
  findings: Record<string, unknown>[];
  total_findings: number;
}

export interface BenchmarkRun {
  id: number;
  ts: string;
  scenario: string;
  metric_value: number;
  metric_unit: string;
  passed: boolean;
}

export interface DashboardWidget {
  id: string;
  type: string; // timeseries, top_n, heatmap, log_table
  title: string;
  query: string;
}

export interface DashboardLayout {
  owner: string;
  widgets: DashboardWidget[];
}

export interface AuditEntry {
  id: number;
  ts: string;
  actor: string;
  method: string;
  path: string;
  status_code: number;
}

export async function fetchPosture(): Promise<PostureRun[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/posture`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /api/posture returned ${res.status}`);
  return (await res.json()) as PostureRun[];
}

export function runPosture(tool: string): Promise<PostureRun> {
  return postJson<PostureRun>(`/api/posture/run?tool=${encodeURIComponent(tool)}`);
}

export async function fetchBenchmarks(): Promise<BenchmarkRun[]> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/benchmark`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /api/benchmark returned ${res.status}`);
  return (await res.json()) as BenchmarkRun[];
}

export function runBenchmark(scenario: string): Promise<BenchmarkRun> {
  return postJson<BenchmarkRun>(`/api/benchmark/run?scenario=${encodeURIComponent(scenario)}`);
}

export async function fetchDashboard(owner = "default"): Promise<DashboardLayout> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/dashboard?owner=${owner}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`GET /api/dashboard returned ${res.status}`);
  return (await res.json()) as DashboardLayout;
}

export async function saveDashboard(layout: DashboardLayout): Promise<DashboardLayout> {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/api/dashboard`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(layout),
  });
  if (!res.ok) throw new Error(`PUT /api/dashboard returned ${res.status}`);
  return (await res.json()) as DashboardLayout;
}

// Live widget data: one aggregation per widget, rendered as a chart.
export interface WidgetSeriesPoint {
  label: string;
  value: number;
}

export interface WidgetData {
  type: string;
  field: string;
  series?: WidgetSeriesPoint[];
  events?: EcsEvent[];
}

export async function fetchWidgetData(
  type: string,
  field: string,
  minutes: number,
): Promise<WidgetData> {
  const params = new URLSearchParams({
    type,
    field,
    minutes: String(minutes),
  });
  const res = await fetch(
    `${PUBLIC_BACKEND_URL}/api/dashboard/widget-data?${params.toString()}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `status ${res.status}` }));
    throw new Error(detail.detail || `GET /api/dashboard/widget-data failed (${res.status})`);
  }
  return (await res.json()) as WidgetData;
}
