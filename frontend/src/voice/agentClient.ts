/* Client for the ideation agent (backend/app/routers/ideation.py).
 *
 * A turn streams as server-sent events: ack, sentence…, tool, evidence,
 * novelty, council, done (IDEATION-PIPELINE-DESIGN.md §1.2). Only `sentence`
 * events are meant for speech; each has already passed the fact check.
 */

import type { ProfileDraft } from "../completeness";
import { STAGES, type Stage } from "../lib/stages";

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
  language?: Lang;
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
  | { event: "ack"; data: { session_id: string; action: Action; reply_language?: Lang } }
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
    // The backend's error handler sends error_message; FastAPI's default is detail.
    const b = body as { error_message?: string; detail?: string };
    const detail = b.error_message || b.detail || `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body as T;
}

/** The profile facts the conversation may use: backend ProfileIn, which
 * refuses any other key. The conversation never asks for these again. */
export interface ConversationProfile {
  district?: string;
  stage?: Stage;
  sector?: string; // the startup's domain, in the founder's words
}

/** The allowlisted projection of the browser profile (R081). Only these
 * fields leave the browser; caste category, phone, date of birth and the rest
 * stay, since the conversation has no purpose for them. */
export function profileForConversation(p: ProfileDraft): ConversationProfile {
  const out: ConversationProfile = {};
  const district = p.founder.district?.trim();
  if (district) out.district = district.slice(0, 80);
  const stage = p.startup.stage;
  if (stage && (STAGES as readonly string[]).includes(stage)) out.stage = stage as Stage;
  const domain = p.startup.domain?.trim();
  if (domain) out.sector = domain.slice(0, 120);
  return out;
}

export function startSession(
  name: string,
  isPrivate: boolean,
  profile?: ConversationProfile,
): Promise<StartResult> {
  const known = profile && Object.keys(profile).length ? profile : null;
  return fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name || null, private: isPrivate, profile: known }),
  }).then((r) => json<StartResult>(r));
}

export function getSession(id: string): Promise<Snapshot> {
  return fetch(`${BASE}/${id}`).then((r) => json<Snapshot>(r));
}

export interface Notices {
  evidence: (e: Evidence) => void;
  novelty: (n: Novelty) => void;
  council: (c: CouncilBrief) => void;
}

/** Background work as it finishes (the search, the novelty check, the review
 * panel), so the panels fill in before the next turn. Returns a function that
 * stops listening. The browser reconnects by itself if the connection drops. */
export function listenNotices(id: string, on: Notices): () => void {
  const src = new EventSource(`${BASE}/${id}/notices`);
  for (const kind of ["evidence", "novelty", "council"] as const) {
    src.addEventListener(kind, (e) => {
      try {
        on[kind](JSON.parse((e as MessageEvent).data));
      } catch {
        /* a malformed notice: the next turn brings the same result */
      }
    });
  }
  return () => src.close();
}

export type Lang = "ta-IN" | "en-IN" | "hi-IN";

export interface VoiceStatus {
  provider: "sarvam" | "browser"; // who listens
  speech: "sarvam" | "gemini" | "phrasebook" | "none"; // who speaks (never the browser)
  phrases_recorded: number;
  languages: Record<Lang, string>;
  voice: string | Record<Lang, string> | null;
}

export function voiceStatus(): Promise<VoiceStatus> {
  return fetch("/api/v1/voice/status").then((r) => json<VoiceStatus>(r));
}

/** Sentences in the mentor's voice: Sarvam (MP3), Gemini or a recording (WAV).
 * Rejects when the server has no audio for them; the words are then only shown. */
export async function speakAudio(text: string, language: Lang): Promise<Blob> {
  const res = await fetch("/api/v1/voice/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) await json(res);
  if (res.status === 204) throw new Error("no recording of this sentence");
  return res.blob();
}

/** One utterance to text; "auto" lets the service detect Tamil, English or Hindi. */
export function transcribe(
  audio: Blob,
  language: Lang | "auto",
): Promise<{ text: string; language: Lang; confidence: number | null }> {
  const form = new FormData();
  const ext = audio.type.includes("ogg") ? "ogg" : audio.type.includes("mp4") ? "m4a" : "webm";
  form.append("file", audio, `turn.${ext}`);
  form.append("language", language);
  return fetch("/api/v1/voice/transcribe", { method: "POST", body: form }).then((r) =>
    json<{ text: string; language: Lang; confidence: number | null }>(r),
  );
}

/** Parse a server-sent event stream into events, as they arrive. */
export async function streamTurn(
  sessionId: string,
  text: string,
  onEvent: (ev: AgentEvent) => void,
  signal?: AbortSignal,
  language?: Lang,
): Promise<void> {
  const res = await fetch(`${BASE}/${sessionId}/turns/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(language ? { text, language } : { text }),
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
