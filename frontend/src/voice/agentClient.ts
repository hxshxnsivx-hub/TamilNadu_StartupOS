/* Client for the ideation agent (backend/app/routers/ideation.py).
 *
 * A turn streams as server-sent events: ack, sentence…, tool, evidence,
 * novelty, council, done (IDEATION-PIPELINE-DESIGN.md §1.2). Only `sentence`
 * events are meant for speech; each has already passed the fact check.
 */

const BASE = "/api/v1/ideation/agent/sessions";

export interface Action {
  kind: "ask" | "confirm" | "generate" | "done";
  slot: string | null;
  question: string | null;
  objective: string | null;
  progress: number;
}

export interface StartResult {
  session_id: string;
  reply: string;
  saved: boolean;
}

export interface CouncilBrief {
  band: "strong" | "mixed" | "weak";
  brief: string[];
  question: string | null;
  blockers: Array<{ seat: string; text: string }>;
  variants: string[];
  stances: Record<string, string>;
  basis: string;
}

export interface Novelty {
  statement: { type: string; text: string };
  levers: Array<{ kind: string; text: string; because: string }>;
  pairs: Array<{ a: string; b: string; papers: number; gap: boolean }>;
  caveat: string;
}

export interface Evidence {
  fields: Array<{ name: string; share_pct: number | null }>;
  papers: { total: number; most_relevant: Array<{ title: string; year: number; url: string }> };
  trials: { total: number; items: Array<{ id: string; title: string; url: string }> };
  projects: { total: number; items: Array<{ name: string; description: string; url: string }> };
  patents: { total: number };
  local: { startups: Array<{ name: string; district: string }> };
  coverage: Array<{ source: string; status: string; note: string }>;
  caveat: string;
}

export interface Done {
  session_id: string;
  reply: string;
  action: Action;
  tools_used: string[];
  dropped: number;
  evidence: Evidence | null;
  novelty: Novelty | null;
  council: CouncilBrief | null;
  roadmap: unknown;
  known: Record<string, string>;
  model?: string;
}

export interface Snapshot {
  session_id: string;
  name: string;
  private: boolean;
  last_question: string | null;
  transcript: Array<{ role: "user" | "assistant"; text: string }>;
  evidence: Evidence | null;
  novelty: Novelty | null;
  council: CouncilBrief | null;
}

export type AgentEvent =
  | { event: "ack"; data: { session_id: string; action: Action } }
  | { event: "sentence"; data: string }
  | { event: "tool"; data: { name: string; status: "started" | "done" } }
  | { event: "evidence"; data: Evidence }
  | { event: "novelty"; data: Novelty }
  | { event: "council"; data: CouncilBrief }
  | { event: "done"; data: Done }
  | { event: "error"; data: { detail: string } };

async function json<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: string }).detail || `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export function startSession(name: string, isPrivate: boolean): Promise<StartResult> {
  return fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name || null, private: isPrivate }),
  }).then((r) => json<StartResult>(r));
}

export function getSession(id: string): Promise<Snapshot> {
  return fetch(`${BASE}/${id}`).then((r) => json<Snapshot>(r));
}

/** Parse a server-sent event stream into events, as they arrive. */
export async function streamTurn(
  sessionId: string,
  text: string,
  onEvent: (ev: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/${sessionId}/turns/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok || !res.body) {
    await json(res); // throws with the server's message
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let cut: number;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, cut);
      buf = buf.slice(cut + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (!data.length) continue;
      try {
        onEvent({ event, data: JSON.parse(data.join("\n")) } as AgentEvent);
      } catch {
        /* a malformed event is skipped, never fatal */
      }
    }
  }
}
