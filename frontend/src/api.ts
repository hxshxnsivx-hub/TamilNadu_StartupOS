// Thin API client for the Vanigam backend (proxied to :8000 in dev).

const TOKEN_KEY = "vanigam_tokens";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function getTokens(): TokenPair | null {
  const raw = localStorage.getItem(TOKEN_KEY);
  return raw ? (JSON.parse(raw) as TokenPair) : null;
}

export function setTokens(t: TokenPair | null) {
  if (t) localStorage.setItem(TOKEN_KEY, JSON.stringify(t));
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  code: string;
  status: number;
  /* The backend attaches `suggestions[]` to every error, and they are the
     whole point: a refusal that names the remedy is the product's central
     claim. Dropping them here would have forced every screen to render
     "Request failed" where the server had actually said what to do instead. */
  suggestions: string[];
  details: unknown;
  constructor(
    status: number,
    code: string,
    message: string,
    suggestions: string[] = [],
    details: unknown = null,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.suggestions = suggestions;
    this.details = details;
  }
}

async function request<T>(path: string, opts: RequestInit = {}, auth = false): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (auth) {
    const t = getTokens();
    if (t) headers["Authorization"] = `Bearer ${t.access_token}`;
  }
  const res = await fetch(`/api/v1${path}`, { ...opts, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      res.status,
      body.error_code || "ERROR",
      body.error_message || `Request failed (${res.status})`,
      Array.isArray(body.suggestions) ? body.suggestions : [],
      body.error_details ?? null,
    );
  }
  return body as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<TokenPair>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ user_id: string; email: string; is_active: boolean }>("/auth/me", {}, true),
  version: () => fetch("/api/v1/version").then((r) => r.json()),
  roadmap: (text: string, language = "en") =>
    request<RoadmapOut>("/ideation/roadmap", {
      method: "POST",
      body: JSON.stringify({ text, language }),
    }),
  recommendSchemes: (body: RecommendIn) =>
    request<RecommendOut>("/schemes/recommend", { method: "POST", body: JSON.stringify(body) }),
  matchB2B: (body: B2BDemandIn) =>
    request<B2BMatchOut>("/b2b/match", { method: "POST", body: JSON.stringify(body) }),
  fundingReadiness: (profile: Record<string, unknown>) =>
    request<ReadinessOut>("/funding/readiness", {
      method: "POST",
      body: JSON.stringify({ profile }),
    }),
  matchInvestors: (body: InvestorMatchIn) =>
    request<InvestorMatchOut>("/funding/investors/match", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  newsBoard: (body: NewsBoardIn = {}) =>
    request<NewsBoardOut>("/news/board", { method: "POST", body: JSON.stringify(body) }),

  /* Decomposes a product into a bill of materials and maps each line onto
     suppliers. The BOM it returns is a DRAFT — the spec requires a human to
     confirm or edit it before matching is acted on, so the UI must never
     auto-commit what comes back from here. */
  decompose: (body: DecomposeIn) =>
    request<DecomposeOut>("/b2b/decompose", { method: "POST", body: JSON.stringify(body) }),

  pipelineBoard: (entries: PipelineEntry[]) =>
    request<PipelineBoardOut>("/funding/pipeline/board", {
      method: "POST",
      body: JSON.stringify({ entries }),
    }),

  pipelineAdvance: (entry: PipelineEntry, to_stage: string) =>
    request<PipelineAdvanceOut>("/funding/pipeline/advance", {
      method: "POST",
      body: JSON.stringify({ entry, to_stage }),
    }),

  /* kind ∈ cin | gstin | pan | dpiit. The response carries a MASKED value —
     the raw identifier is never echoed back, and the UI never stores it. */
  verify: (kind: string, value: string) =>
    request<VerificationOut>(`/verify/${kind}`, {
      method: "POST",
      body: JSON.stringify({ value }),
    }),
};

/* ---------------- product decomposition ---------------- */

export interface DecomposeIn {
  product: string;
  monthly_units: number;
  district?: string;
  state?: string;
}
export interface BOMLine {
  category: string;
  spec: string;
  qty_per_unit: number;
  unit: string;
}
export interface SupplyMapLine {
  line: BOMLine;
  gap: boolean;
  matches: B2BMatchItem[];
}
export interface DecomposeOut {
  product: string;
  monthly_units: number;
  bom: BOMLine[];
  supply_map: SupplyMapLine[];
  gaps: number;
}

/* ---------------- funding pipeline ---------------- */

export interface PipelineHistoryItem {
  stage: string;
  at: string;
}
export interface PipelineEntry {
  investor_id: string;
  investor_name?: string;
  stage: string;
  amount: number;
  history: PipelineHistoryItem[];
}
export interface PipelineColumn {
  stage: string;
  count: number;
  value: number;
  entries: PipelineEntry[];
}
export interface PipelineMetrics {
  total: number;
  by_stage: Record<string, number>;
  open_count: number;
  won: number;
  lost: number;
  win_rate: number;
  stage_conversion: Record<string, number>;
  avg_days_in_stage: Record<string, number>;
  pipeline_value: number;
  weighted_value: number;
}
export interface PipelineBoardOut {
  stages: string[];
  columns: PipelineColumn[];
  metrics: PipelineMetrics;
}
export interface PipelineAdvanceOut {
  entry: PipelineEntry;
  next_stages: string[];
}

/* ---------------- legal verification ---------------- */

export interface VerificationOut {
  kind: string;
  value_masked: string;
  verified: boolean;
  status: string;
  source: string;
  reason: string | null;
  details: Record<string, unknown>;
}

export interface NewsBoardIn {
  founder?: Record<string, unknown>;
  limit?: number;
  language?: string;
}
export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  url: string;
  source_id: string;
  source_name: string;
  tier: string;
  published: string;
  language: string;
  tags: string[];
  score: number;
  why: string[];
  duplicates: string[];
}
export interface NewsSource {
  id: string;
  name: string;
  domain: string;
  tier: string;
  language: string;
  verified: boolean;
  fetchable: boolean;
}
export interface NewsBoardOut {
  provider: string;
  is_live: boolean;
  generated: string;
  total_fetched: number;
  items: NewsItem[];
  sources: NewsSource[];
  notice: string;
}

export interface ReadinessGap {
  dimension: string;
  action: string;
  impact: string;
  impact_points: number;
  effort_weeks: number;
}
export interface ReadinessOut {
  overall: number;
  band: string;
  dimensions: Record<string, number>;
  gaps: ReadinessGap[];
}
export interface InvestorMatchIn {
  startup: Record<string, unknown>;
  funding_need: number;
  readiness_overall: number;
}
export interface InvestorInfo {
  id: string;
  name: string;
  type: string;
  min_ticket: number;
  max_ticket: number;
  track_record_score: number;
  thesis: string;
}
export interface EligibleInvestor {
  investor: InvestorInfo;
  fit: number;
}
export interface IneligibleInvestor {
  investor: InvestorInfo;
  reasons: string[];
}
export interface InvestorMatchOut {
  total_checked: number;
  eligible: EligibleInvestor[];
  ineligible: IneligibleInvestor[];
}

export interface B2BDemandIn {
  category: string;
  spec: string;
  quantity: number;
  budget_per_unit: number;
  district: string;
  state: string;
}
export interface B2BSupply {
  id: string;
  name: string;
  category: string;
  unit_price: number;
  max_capacity: number;
  min_order: number;
  district: string;
  state: string;
  trust_score: number;
  payment_mode: string;
}
export interface B2BBreakdown {
  spec_similarity: number;
  price_fit: number;
  capacity_fit: number;
  geo_proximity: number;
}
export interface B2BMatchItem {
  supply: B2BSupply;
  weight: number;
  base_weight: number;
  breakdown: B2BBreakdown;
}
export interface B2BMatchOut {
  category: string;
  count: number;
  matches: B2BMatchItem[];
}

export interface RecommendIn {
  founder: Record<string, unknown>;
  startup: Record<string, unknown>;
  funding_need?: number | null;
}
export interface SchemeInfo {
  id: string;
  name: string;
  level: string;
  type: string;
  max_funding: number;
  benefits: string;
  source_url: string;
  last_verified: string;
}
export interface RankedScheme {
  scheme: SchemeInfo;
  relevance: number;
  likelihood: number;
  why: string[];
}
export interface IneligibleScheme {
  scheme: SchemeInfo;
  reasons: string[];
}
export interface RecommendOut {
  total_checked: number;
  ranked_eligible: RankedScheme[];
  ineligible: IneligibleScheme[];
}

export interface Milestone {
  id: string;
  phase: string;
  title: string;
  deliverables: string[];
  timeline: { optimistic: number; realistic: number; pessimistic: number };
  depends_on: string[];
  critical: boolean;
}
export interface RoadmapOut {
  idea: {
    problem: string | null;
    solution: string | null;
    target_market: string | null;
    value_proposition: string | null;
    differentiation: string | null;
    domain: string | null;
    missing_elements: string[];
  };
  feasibility_score: number;
  feasibility_breakdown: Record<string, number>;
  milestones: Milestone[];
  critical_path: string[];
  clarifications: string[];
}
