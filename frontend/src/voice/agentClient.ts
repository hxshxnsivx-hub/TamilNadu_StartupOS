/* Client for the ideation agent (backend/app/routers/ideation.py).
 *
 * A turn streams as server-sent events: ack, sentence…, tool, evidence,
 * novelty, council, done (IDEATION-PIPELINE-DESIGN.md §1.2). Only `sentence`
 * events are meant for speech; each has already passed the fact check.
 */

import type { ProfileDraft } from "../completeness";
import type { EntryMode, Journey, RegSubtype } from "../journeyStore";
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
  replayed?: boolean; // a retry of a turn the server had already saved
}

/** What the founder is being asked right now (backend PendingAction, R176). */
export interface PendingAction {
  kind: "ask" | "confirm" | "choose_card" | "choose_lever";
  slot: string | null;
  question: string | null;
  options: string[];
  idea_version: string | null;
}

export interface Snapshot {
  session_id: string;
  name: string;
  private: boolean;
  entry_mode: EntryMode | null;
  reg_subtype: RegSubtype | null;
  last_question: string | null;
  pending: PendingAction | null;
  /** After a long gap: welcome back and the pending question again (1.1.4.3). */
  resume: string | null;
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
  | { event: "done"; data: Done };

/** Why a turn did not finish (R076, R159):
 * - conflict: the conversation changed elsewhere; the reply was not saved
 * - expired: hidden after 6 hours idle, but still stored: keep the id, so the
 *   founder can still delete it (R107)
 * - gone: no such conversation (deleted, or never saved): the id is useless
 * - failed: the server could not finish the turn
 * - truncated: the stream ended before `done`; the turn was not saved
 * - network: the request never reached the server */
export type TurnErrorCode = "conflict" | "expired" | "gone" | "failed" | "truncated" | "network";

export class TurnError extends Error {
  code: TurnErrorCode;
  constructor(code: TurnErrorCode, message: string) {
    super(message);
    this.name = "TurnError";
    this.code = code;
  }
}

/** Worth sending again with the same turn id: the server either replays the
 * saved turn or runs it for the first time, never twice. */
export function retryable(e: unknown): boolean {
  return e instanceof TurnError && (e.code === "truncated" || e.code === "network");
}

/** A name for one turn, kept across its retries (backend AgentTurnIn.client_turn_id). */
export function newTurnId(): string {
  try {
    if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  } catch {
    /* not a secure context: fall back below */
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

async function failure(res: Response): Promise<TurnError> {
  const body = await res.json().catch(() => ({}));
  const b = body as { error_message?: string; detail?: string };
  const detail = b.error_message || b.detail || `Request failed (${res.status})`;
  const code: TurnErrorCode =
    res.status === 410
      ? "expired"
      : res.status === 404
        ? "gone"
        : res.status === 409
          ? "conflict"
          : "failed";
  return new TurnError(code, detail);
}

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

/** The Start screen's two answers, as backend AgentStartIn takes them (task
 * 1.1.6): a registered founder is greeted about the product and not asked the
 * stage the subtype implies. Only these two fields of the journey leave the
 * browser; consent and milestones stay. */
export interface ConversationEntry {
  entry_mode?: EntryMode;
  reg_subtype?: RegSubtype;
}

export function entryForConversation(j: Journey): ConversationEntry {
  const out: ConversationEntry = {};
  if (j.entry_mode) out.entry_mode = j.entry_mode;
  if (j.reg_subtype) out.reg_subtype = j.reg_subtype;
  return out;
}

export function startSession(
  name: string,
  isPrivate: boolean,
  profile?: ConversationProfile,
  entry: ConversationEntry = {},
): Promise<StartResult> {
  const known = profile && Object.keys(profile).length ? profile : null;
  return fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: name || null,
      private: isPrivate,
      profile: known,
      entry_mode: entry.entry_mode ?? null,
      reg_subtype: entry.reg_subtype ?? null,
    }),
  }).then((r) => json<StartResult>(r));
}

/** Rejects with TurnError: `expired` when it is hidden but still stored (keep
 * the id: it can still be deleted), `gone` when there is no such conversation,
 * `network` when the server could not be reached (the id is worth keeping). */
export async function getSession(id: string): Promise<Snapshot> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/${id}`);
  } catch {
    throw new TurnError("network", "Could not reach Vanigam.");
  }
  if (!res.ok) throw await failure(res);
  return (await res.json()) as Snapshot;
}

/** Delete a conversation (also one that expired) with its transcript, evidence
 * and roadmap. Resolves when the server no longer holds it, including when it
 * was already gone. Rejects with TurnError (`network`, `failed`): the id is then
 * still needed to try again. */
export async function deleteSession(id: string): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  } catch {
    throw new TurnError("network", "Could not reach Vanigam.");
  }
  if (res.ok || res.status === 404) return;
  throw await failure(res);
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

/** Parse a server-sent event stream into events, as they arrive.
 *
 * Resolves only when `done` arrived: that is the server's sign the turn was
 * saved. Otherwise rejects with a TurnError: an `error` event's code, or
 * `truncated` when the stream stopped first, or `network` (R076, R159).
 * `clientTurnId` names the turn; send the same one again to retry it. */
export async function streamTurn(
  sessionId: string,
  text: string,
  onEvent: (ev: AgentEvent) => void,
  signal?: AbortSignal,
  language?: Lang,
  clientTurnId?: string,
): Promise<void> {
  const body: Record<string, string> = { text };
  if (language) body.language = language;
  if (clientTurnId) body.client_turn_id = clientTurnId;
  let res: Response;
  try {
    res = await fetch(`${BASE}/${sessionId}/turns/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new TurnError("network", "Could not reach Vanigam.");
  }
  if (!res.ok) throw await failure(res);
  if (!res.body) throw new TurnError("truncated", "The reply did not arrive.");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    let chunk: ReadableStreamReadResult<Uint8Array>;
    try {
      chunk = await reader.read();
    } catch (e) {
      if (signal?.aborted) throw e;
      throw new TurnError("truncated", "The connection dropped during the reply.");
    }
    const { value, done } = chunk;
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
      let parsed: unknown;
      try {
        parsed = JSON.parse(data.join("\n"));
      } catch {
        continue; // a malformed event is skipped, never fatal
      }
      if (event === "error") {
        const e = parsed as { code?: TurnErrorCode; detail?: string };
        void reader.cancel().catch(() => undefined);
        throw new TurnError(e.code ?? "failed", e.detail ?? "The turn failed.");
      }
      onEvent({ event, data: parsed } as AgentEvent);
      if (event === "done") return; // saved: anything after it is not part of the turn
    }
  }
  throw new TurnError("truncated", "The reply stopped before it finished.");
}
