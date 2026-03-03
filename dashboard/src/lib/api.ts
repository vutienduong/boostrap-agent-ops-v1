const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface RunSummary {
  id: string;
  project_id: string;
  name: string | null;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  tags: Record<string, string> | null;
}

export interface Span {
  id: string;
  run_id: string;
  parent_span_id: string | null;
  type: string;
  name: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  status: string;
  model: string | null;
  tokens_prompt: number;
  tokens_completion: number;
  cost_usd: number;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  error_json: Record<string, unknown> | null;
}

export interface RunDetail extends RunSummary {
  spans: Span[];
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
}

export async function fetchRuns(
  projectId: string
): Promise<{ runs: RunSummary[]; cursor: string | null }> {
  const res = await fetch(`${API_URL}/v1/runs?project_id=${projectId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${API_URL}/v1/runs/${runId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

export interface CostByDay {
  date: string;
  cost_usd: number;
  prompt_tokens: number;
  completion_tokens: number;
  run_count: number;
}

export interface CostByModel {
  model: string;
  cost_usd: number;
  prompt_tokens: number;
  completion_tokens: number;
  span_count: number;
}

export interface CostMetrics {
  total_cost_usd: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  by_day: CostByDay[];
  by_model: CostByModel[];
}

export async function fetchCostMetrics(projectId: string): Promise<CostMetrics> {
  const res = await fetch(
    `${API_URL}/v1/metrics/cost?project_id=${projectId}`,
    { cache: "no-store", headers: { "X-AgentOps-Key": "dev_agentops_key_local" } }
  );
  if (!res.ok) throw new Error("Failed to fetch cost metrics");
  return res.json();
}

export interface PromptVersion {
  id: string;
  project_id: string;
  key: string;
  version: string;
  content: string;
  meta: Record<string, unknown> | null;
  created_at: string;
}

export async function fetchPromptVersions(
  projectId: string,
  key?: string
): Promise<{ versions: PromptVersion[] }> {
  const params = new URLSearchParams({ project_id: projectId });
  if (key) params.append("key", key);
  const res = await fetch(`${API_URL}/v1/prompts?${params}`, {
    cache: "no-store",
    headers: { "X-AgentOps-Key": "dev_agentops_key_local" },
  });
  if (!res.ok) throw new Error("Failed to fetch prompts");
  return res.json();
}
