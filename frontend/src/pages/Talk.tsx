/* Talk: the voice ideation agent (Phase 3).
 *
 * The founder talks to the orb or types; replies stream sentence by sentence
 * and are spoken as they arrive. Every claim the agent makes can be checked in
 * the evidence panel below. Text input is always available: voice is a
 * convenience, never a requirement.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Orb, { type OrbState } from "../voice/Orb";
import {
  deleteSession,
  entryForConversation,
  getSession,
  listenNotices,
  newTurnId,
  profileForConversation,
  retryable,
  startSession,
  streamTurn,
  TurnError,
  voiceStatus,
  type Action,
  type AgentEvent,
  type Snapshot,
  type Lang,
  type CouncilBrief,
  type Evidence,
  type Novelty,
  type VoiceStatus,
} from "../voice/agentClient";
import { Listener, canListen, isBargeIn, micLevel } from "../voice/speech";
import { AudioSpeaker, RecordingListener } from "../voice/mentorVoice";
import { loadJourney } from "../journeyStore";
import { loadProfile } from "../profileStore";

const LANGS: Lang[] = ["ta-IN", "en-IN", "hi-IN"];

const SESSION_KEY = "vanigam_talk_session";
const TOOL_LABEL: Record<string, string> = {
  scan_prior_art: "Looking up what already exists",
  check_novelty: "Checking what is rare",
  ask_council: "Asking the review panel",
  build_roadmap: "Building your roadmap",
  find_domains: "Finding the closest domains",
  support_for: "Finding schemes and incubators",
  note_fact: "Noting that",
};

type Line = { role: "user" | "assistant"; text: string };

// A turn cut off by the network is sent again with the same id after these
// pauses (ms): the server replays it if it was saved, or runs it once (R076).
const RETRY_WAIT_MS = [1000, 3000, 7000];
// Said when another screen changed the conversation and this reply was not kept (R159).
const CONFLICT_LINE = "This conversation changed on another screen, so I reloaded it.";
/** The conflict line, plus what the founder said that was not kept: never resent
 * by itself, since the other screen may already have answered. */
const lostLine = (said: string) =>
  `${CONFLICT_LINE} What you just said was not kept: "${said}". Please say it again.`;
// Hidden after 6 idle hours, but still stored: the id is kept so the founder can
// delete it (R107). Starting fresh drops the id and leaves the stored copy.
const EXPIRED_LINE =
  "Your last conversation ended after 6 hours without activity. It is still stored on Vanigam's server: you can delete it, or start fresh and leave it stored.";
const GONE_LINE = "Your last conversation is no longer stored, so this is a fresh start.";
const DELETED_LINE =
  "Your conversation is deleted: its transcript, evidence and roadmap are gone from Vanigam.";
const CONFIRM_DELETE =
  "Delete this conversation? Its transcript, evidence and roadmap are erased from Vanigam. This cannot be undone.";

const pause = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

function readSaved(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}
function save(id: string | null) {
  try {
    if (id) localStorage.setItem(SESSION_KEY, id);
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    /* private window: the conversation still works, it just won't resume */
  }
}

export default function Talk() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [isPrivate, setPrivate] = useState(false);
  const [saved, setSaved] = useState<boolean | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [caption, setCaption] = useState("");
  const [partial, setPartial] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [level, setLevel] = useState(0);
  const [voiceOn, setVoiceOn] = useState(true);
  const [lang, setLang] = useState<Lang | "auto">("auto");
  const [provider, setProvider] = useState<"browser" | "sarvam">("browser"); // who listens
  const [speech, setSpeech] = useState<VoiceStatus["speech"]>("none");
  const [draft, setDraft] = useState("");
  const [action, setAction] = useState<Action | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [novelty, setNovelty] = useState<Novelty | null>(null);
  const [council, setCouncil] = useState<CouncilBrief | null>(null);
  // a conversation that expired but is still stored: kept to offer deleting it
  const [expiredId, setExpiredId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState("");

  const busyRef = useRef(false);
  const turnAbortRef = useRef<AbortController | null>(null); // the turn now streaming
  const mutedRef = useRef(false); // founder interrupted: stop speaking this turn
  // what the founder said while a turn was busy: all of it goes in the next turn (R144)
  const queuedRef = useRef<string[]>([]);
  const stopMicRef = useRef<(() => void) | null>(null);
  const voiceOnRef = useRef(voiceOn);
  voiceOnRef.current = voiceOn;
  const founderLangRef = useRef<Lang | undefined>(undefined); // last language heard
  const langRef = useRef(lang);
  langRef.current = lang;

  // The mentor's voice comes from the server: Sarvam, Gemini's free voice, or the
  // recorded phrasebook. Never the browser's own voice; with none, replies are shown.
  useEffect(() => {
    voiceStatus()
      .then((v) => {
        setProvider(v.provider);
        setSpeech(v.speech ?? "none");
      })
      .catch(() => {
        setProvider("browser");
        setSpeech("none");
      });
  }, []);

  const speaker = useMemo(() => {
    const ev = {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
      onPulse: (v: number) => setLevel(v),
    };
    // Gemini and Sarvam take several sentences per request; recordings, one each
    return new AudioSpeaker(ev, speech === "gemini" || speech === "sarvam");
  }, [speech]);

  /** The language to send with a turn: chosen, or last heard when on auto. */
  const turnLang = (heard?: Lang): Lang | undefined =>
    langRef.current === "auto" ? heard ?? founderLangRef.current : langRef.current;

  /** Show a conversation as the server holds it; `lead` is said before the
   * pending question (after a long gap the server writes its own preamble). */
  function show(snap: Snapshot, lead?: string) {
    setSessionId(snap.session_id);
    setName(snap.name === "there" ? "" : snap.name);
    setPrivate(snap.private);
    setLines(snap.transcript);
    setEvidence(snap.evidence);
    setNovelty(snap.novelty);
    setCouncil(snap.council);
    const question = snap.pending?.question ?? snap.last_question ?? "";
    const say = lead ? `${lead} ${question}`.trim() : snap.resume ?? "";
    setCaption(say || question);
    if (say && voiceOnRef.current) speaker.say(say, "en-IN");
  }

  // ---- resume a saved conversation
  useEffect(() => {
    const id = readSaved();
    if (!id) return;
    getSession(id)
      .then((snap) => show(snap))
      .catch((e) => {
        if (e instanceof TurnError && e.code === "expired") {
          setExpiredId(id); // kept: the founder may still delete it (R107)
        } else if (e instanceof TurnError && e.code === "gone") {
          save(null); // nothing left to resume or delete: start fresh, and say why
          setError(GONE_LINE);
        } else {
          setError("Could not reach Vanigam. Your conversation is kept; reload to try again.");
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- slow work (search, novelty, review panel) shows up the moment it finishes
  useEffect(() => {
    if (!sessionId) return;
    return listenNotices(sessionId, {
      evidence: setEvidence,
      novelty: setNovelty,
      council: setCouncil,
    });
  }, [sessionId]);

  // ---- one turn
  const send = useCallback(
    async (text: string, heardLang?: Lang) => {
      const said = text.trim();
      if (!said || !sessionId) return;
      if (busyRef.current) {
        queuedRef.current.push(said); // sent, joined, when this turn finishes
        return;
      }
      busyRef.current = true;
      mutedRef.current = false;
      const ctl = new AbortController(); // a delete stops this turn
      turnAbortRef.current = ctl;
      setBusy(true);
      setError("");
      setPartial("");
      setLines((l) => [...l, { role: "user", text: said }]);
      let spoken = "";
      let replyLang: Lang = "en-IN";
      let kept = true; // false when the server did not keep this turn
      // One id for this turn and all its retries; what was already said aloud in
      // an attempt cut short is not said again when the retry brings it back.
      const turnId = newTurnId();
      const heard: string[] = [];
      let n = 0;
      const onEvent = (ev: AgentEvent) => {
        switch (ev.event) {
          case "ack":
            setAction(ev.data.action);
            replyLang = ev.data.reply_language ?? "en-IN";
            break;
          case "sentence": {
            spoken = spoken ? `${spoken} ${ev.data}` : ev.data;
            const again = heard[n] === ev.data;
            heard[n++] = ev.data;
            if (again) break;
            setCaption(ev.data);
            setStatus("");
            if (voiceOnRef.current && !mutedRef.current) speaker.say(ev.data, replyLang);
            break;
          }
          case "tool":
            setStatus(ev.data.status === "started" ? `${TOOL_LABEL[ev.data.name] ?? ev.data.name}…` : "");
            break;
          case "evidence":
            setEvidence(ev.data);
            break;
          case "novelty":
            setNovelty(ev.data);
            break;
          case "council":
            setCouncil(ev.data);
            break;
          case "done":
            speaker.flush(); // the reply is complete: say what is still waiting
            setAction(ev.data.action);
            if (ev.data.evidence) setEvidence(ev.data.evidence);
            if (ev.data.novelty) setNovelty(ev.data.novelty);
            if (ev.data.council) setCouncil(ev.data.council);
            spoken = ev.data.reply || spoken;
            break;
        }
      };
      try {
        for (let attempt = 0; ; attempt++) {
          spoken = "";
          n = 0;
          try {
            await streamTurn(sessionId, said, onEvent, ctl.signal, turnLang(heardLang), turnId);
            break;
          } catch (e) {
            if (ctl.signal.aborted || !retryable(e) || attempt >= RETRY_WAIT_MS.length) throw e;
            setStatus("The connection dropped; trying again…");
            await pause(RETRY_WAIT_MS[attempt]);
            if (ctl.signal.aborted) throw e;
          }
        }
      } catch (e) {
        if (ctl.signal.aborted) {
          kept = false; // the founder deleted the conversation mid-turn
          queuedRef.current = [];
        } else if (e instanceof TurnError && e.code === "conflict") {
          // the reply was heard but not kept: take it back and show what is kept
          kept = false;
          speaker.cancel();
          const lost = lostLine(said);
          setDraft(said); // in the box, ready to send again with one tap
          setError(lost); // stays visible after the caption moves on
          try {
            show(await getSession(sessionId), lost);
          } catch {
            setError(`${lost} Reload the page first to continue.`);
          }
        } else if (e instanceof TurnError && e.code === "expired") {
          kept = false; // still stored: keep the id and offer to delete it (R107)
          queuedRef.current = [];
          leave();
          setExpiredId(sessionId);
        } else if (e instanceof TurnError && e.code === "gone") {
          kept = false;
          save(null);
          setError(GONE_LINE + " Press Start over to begin again.");
        } else if (retryable(e)) {
          kept = false;
          setError(
            "The connection keeps dropping, so I could not finish that turn. When the signal is back, reload the page to see where we stopped.",
          );
        } else {
          setError(e instanceof Error ? e.message : "The turn failed. Try again.");
        }
      } finally {
        if (turnAbortRef.current === ctl) turnAbortRef.current = null;
        if (spoken && kept) setLines((l) => [...l, { role: "assistant", text: spoken }]);
        busyRef.current = false;
        setBusy(false);
        setStatus("");
        const next = queuedRef.current.join(" ");
        queuedRef.current = [];
        if (next) void send(next);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sessionId, speaker],
  );
  const sendRef = useRef(send);
  sendRef.current = send;

  // ---- listening
  const browserListener = useMemo(
    () =>
      new Listener({
        onPartial: (t) => {
          setPartial(t);
          if (speaker.speaking && isBargeIn(t, speaker.current)) {
            mutedRef.current = true; // the founder is talking: stop, and listen
            speaker.cancel();
          }
        },
        onFinal: (t) => {
          if (speaker.speaking && !isBargeIn(t, speaker.current)) return; // our own echo
          void sendRef.current(t);
        },
        onSpeechStart: () => undefined,
        onError: (m) => {
          setError(m);
          setListening(false);
        },
      }),
    [speaker],
  );

  const recordingListener = useMemo(
    () =>
      provider !== "sarvam"
        ? null
        : new RecordingListener(
            {
              onPartial: (t) => setPartial(t),
              onFinal: () => undefined,
              onFinalLang: (t, l) => {
                founderLangRef.current = l;
                void sendRef.current(t, l);
              },
              onSpeechStart: () => {
                if (speaker.speaking) {
                  mutedRef.current = true; // the founder is talking: stop, and listen
                  speaker.cancel();
                }
              },
              onUtteranceEnd: () => {
                // no dead air: acknowledge at once, in the founder's language
                if (voiceOnRef.current && speaker instanceof AudioSpeaker) {
                  speaker.acknowledge(turnLang() ?? "en-IN");
                }
              },
              onLevel: (v) => {
                if (!speaker.speaking) setLevel(v);
              },
              onError: (m) => {
                setError(m);
                setListening(false);
              },
            },
            () => speaker.speaking,
          ),
    [provider, speaker],
  );
  const listener = recordingListener ?? browserListener;

  useEffect(() => {
    // Browser recognition needs one language; Sarvam can detect it ("auto").
    const l = lang === "auto" && !recordingListener ? "en-IN" : lang;
    browserListener.lang = l;
    browserListener.setLang(l);
    recordingListener?.setLang(lang);
  }, [lang, browserListener, recordingListener]);

  const stopListening = useCallback(() => {
    listener.stop();
    stopMicRef.current?.();
    stopMicRef.current = null;
    setListening(false);
    setLevel(0);
    setPartial("");
  }, [listener]);

  const startListening = useCallback(async () => {
    setError("");
    if (recordingListener) {
      setListening(true);
      await recordingListener.start(); // its own level meter
      return;
    }
    if (!canListen) {
      setError("This browser has no speech recognition. Type below instead.");
      return;
    }
    listener.start();
    setListening(true);
    try {
      stopMicRef.current = await micLevel((v) => {
        if (!speaker.speaking) setLevel(v);
      });
    } catch {
      /* no level meter: recognition still works */
    }
  }, [listener, recordingListener, speaker]);

  useEffect(() => () => {
    stopListening();
    speaker.cancel();
  }, [stopListening, speaker]);

  // ---- starting and ending a conversation
  async function begin() {
    setError("");
    setNotice("");
    try {
      // what the profile and the Start screen already say is never asked again
      // (tasks 1.1.1, 1.1.6)
      const r = await startSession(
        name.trim(),
        isPrivate,
        profileForConversation(loadProfile()),
        entryForConversation(loadJourney()),
      );
      setSessionId(r.session_id);
      setSaved(r.saved);
      save(r.session_id);
      setLines([{ role: "assistant", text: r.reply }]);
      setCaption(r.reply);
      if (voiceOn) speaker.say(r.reply, "en-IN");
      if (speaker instanceof AudioSpeaker) speaker.warm(LANGS);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start. Is the backend running?");
    }
  }

  /** Close the conversation on this screen; the saved id is left as it is. */
  function leave() {
    stopListening();
    speaker.cancel();
    queuedRef.current = [];
    setSessionId(null);
    setLines([]);
    setCaption("");
    setEvidence(null);
    setNovelty(null);
    setCouncil(null);
    setAction(null);
  }

  function startOver() {
    leave();
    save(null);
  }

  /** Erase a conversation on the server. The id is dropped only once the server
   * confirms; on a failure it is kept, so the founder can try again (R107). */
  async function remove(id: string) {
    if (!window.confirm(CONFIRM_DELETE)) return;
    setDeleting(true);
    setError("");
    turnAbortRef.current?.abort(); // a reply still streaming stops; the server waits for it to end
    try {
      await deleteSession(id);
    } catch (e) {
      const why = e instanceof Error ? e.message : "The delete failed.";
      setError(`Could not delete the conversation: ${why} It is kept here; try again.`);
      return;
    } finally {
      setDeleting(false);
    }
    setExpiredId(null);
    startOver();
    setNotice(DELETED_LINE);
  }

  const orbState: OrbState = speaking ? "speaking" : busy ? "thinking" : listening ? "listening" : "idle";

  // ---- before the conversation
  if (!sessionId) {
    return (
      <section aria-labelledby="talk-title">
        <h1 id="talk-title">Talk through your idea</h1>
        {notice ? <p role="status">{notice}</p> : null}
        {expiredId ? (
          // the founder chooses before anything else replaces the kept id (R107)
          <section aria-labelledby="talk-expired">
            <h2 id="talk-expired">Your last conversation</h2>
            <p>{EXPIRED_LINE}</p>
            <p>
              <button type="button" onClick={() => void remove(expiredId)} disabled={deleting}>
                {deleting ? "Deleting…" : "Delete it"}
              </button>{" "}
              <button
                type="button"
                disabled={deleting}
                onClick={() => {
                  save(null);
                  setExpiredId(null);
                  setError("");
                }}
              >
                Start fresh
              </button>
            </p>
          </section>
        ) : (
          <>
            <p>
              Describe your idea in your own words, by voice or by typing. I look up what already
              exists (papers, trials, open projects, patents, Tamil Nadu startups), tell you what is
              rare, and ask one question at a time.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void begin();
              }}
            >
              <p>
                <label htmlFor="talk-name">Your name (optional) </label>
                <input id="talk-name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="given-name" />
              </p>
              <p>
                <input id="talk-private" type="checkbox" checked={isPrivate} onChange={(e) => setPrivate(e.target.checked)} />{" "}
                <label htmlFor="talk-private">
                  Private: search only Vanigam's own data, nothing outside it
                </label>
              </p>
              <p>
                <button type="submit">Start</button>
              </p>
            </form>
            {canListen ? (
              <p>
                <small>
                  Voice uses your browser's speech service to turn speech into text; Vanigam receives
                  only the text, and no audio is stored.
                </small>
              </p>
            ) : (
              <p>
                <small>This browser has no speech recognition; you can type.</small>
              </p>
            )}
          </>
        )}
        {error ? <p role="alert">{error}</p> : null}
      </section>
    );
  }

  // ---- the conversation
  return (
    <section aria-labelledby="talk-title">
      <h1 id="talk-title">Talk through your idea</h1>
      {saved === false ? (
        <p>
          <small>This conversation is not being saved (no database); it will be lost on restart.</small>
        </p>
      ) : null}

      <Orb
        state={orbState}
        level={level}
        onToggle={() => {
          if (speaking) {
            mutedRef.current = true;
            speaker.cancel();
            return;
          }
          if (listening) stopListening();
          else void startListening();
        }}
        disabled={!canListen && !recordingListener && !speaking}
      />

      <p className={`vg-caption${partial ? " vg-caption--partial" : ""}`} aria-live="polite">
        {partial || caption}
      </p>
      {status ? <p aria-live="polite">{status}</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          const t = draft;
          setDraft("");
          void send(t);
        }}
      >
        <label htmlFor="talk-input">{action?.question ? "Your answer" : "Type instead"} </label>
        <input
          id="talk-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={action?.question ?? "Describe your idea"}
          size={60}
        />{" "}
        <button type="submit" disabled={!draft.trim()}>
          Send
        </button>{" "}
        {action?.kind === "ask" ? (
          <button type="button" onClick={() => void send("skip")} disabled={busy}>
            Skip question
          </button>
        ) : null}
      </form>

      <p>
        <label htmlFor="talk-lang">I'll speak in </label>
        <select
          id="talk-lang"
          value={lang}
          onChange={(e) => setLang(e.target.value as Lang | "auto")}
        >
          <option value="auto">
            {provider === "sarvam"
              ? "Any: Tamil, English or Hindi"
              : "Auto (the browser listens in English)"}
          </option>
          <option value="ta-IN">தமிழ் (Tamil)</option>
          <option value="en-IN">English (India)</option>
          <option value="hi-IN">हिन्दी (Hindi)</option>
        </select>{" "}
        <input
          id="talk-voice"
          type="checkbox"
          checked={voiceOn && speech !== "none"}
          disabled={speech === "none"}
          onChange={(e) => {
            setVoiceOn(e.target.checked);
            if (!e.target.checked) speaker.cancel();
          }}
        />{" "}
        <label htmlFor="talk-voice">
          {speech === "none" ? "Speak replies aloud (no mentor voice set up)" : "Speak replies aloud"}
        </label>{" "}
        <button type="button" onClick={() => void send("what do you think?")} disabled={busy}>
          What do you think?
        </button>{" "}
        <button type="button" onClick={startOver}>
          Start over
        </button>{" "}
        <button type="button" onClick={() => void remove(sessionId)} disabled={deleting}>
          {deleting ? "Deleting…" : "Delete this conversation"}
        </button>
      </p>
      {action ? (
        <p>
          <small>
            {Math.round(action.progress * 100)}% of the essentials known
            {isPrivate ? " · private mode" : ""}
          </small>
        </p>
      ) : null}

      <h2>Conversation</h2>
      <ol aria-live="off">
        {lines.map((l, i) => (
          <li key={i}>
            <strong>{l.role === "user" ? "You" : "Vanigam"}:</strong> {l.text}
          </li>
        ))}
      </ol>

      <EvidencePanel evidence={evidence} novelty={novelty} council={council} />
    </section>
  );
}

function EvidencePanel({
  evidence,
  novelty,
  council,
}: {
  evidence: Evidence | null;
  novelty: Novelty | null;
  council: CouncilBrief | null;
}) {
  if (!evidence && !novelty && !council) return null;
  const notSearched = (evidence?.coverage ?? []).filter((c) => !["ok", "skipped"].includes(c.status));
  return (
    <section aria-labelledby="ev-title">
      <h2 id="ev-title">Where this comes from</h2>

      {council ? (
        <details open>
          <summary>
            Review panel: {council.band} ({council.basis === "model" ? "Claude" : "rules"})
          </summary>
          <ul>
            {council.brief.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
          {council.blockers.length ? (
            <p>
              <strong>Blockers:</strong> {council.blockers.map((b) => b.text).join("; ")}
            </p>
          ) : null}
          <p>
            <strong>Options:</strong> {council.variants.join(" · ")}
          </p>
          <p>
            <small>
              Seats:{" "}
              {Object.entries(council.stances)
                .map(([seat, stance]) => `${seat.replace("_", " ")} ${stance}`)
                .join(", ")}
            </small>
          </p>
        </details>
      ) : null}

      {novelty ? (
        <details open>
          <summary>What is rare</summary>
          <p>{novelty.statement.text}</p>
          {novelty.pairs.length ? (
            <ul>
              {novelty.pairs.map((p, i) => (
                <li key={i}>
                  {p.a} with {p.b}: {p.papers.toLocaleString("en-IN")} papers
                  {p.gap ? " (rare together)" : ""}
                </li>
              ))}
            </ul>
          ) : null}
          {novelty.levers.length ? (
            <>
              <p>
                <strong>Ways to stand out</strong>
              </p>
              <ul>
                {novelty.levers.map((lv, i) => (
                  <li key={i}>
                    {lv.text} <small>(because {lv.because})</small>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <p>
            <small>{novelty.caveat}</small>
          </p>
        </details>
      ) : null}

      {evidence ? (
        <details>
          <summary>What already exists</summary>
          {evidence.fields.length ? (
            <p>Fields: {evidence.fields.map((f) => f.name).join(", ")}</p>
          ) : null}
          <SourceList
            title={`Clinical trials (${evidence.trials.total})`}
            items={evidence.trials.items.slice(0, 3).map((t) => ({ text: `${t.id}: ${t.title}`, url: t.url }))}
          />
          <SourceList
            title={`Open-source projects (${evidence.projects.total})`}
            items={evidence.projects.items.slice(0, 3).map((g) => ({ text: g.name, url: g.url }))}
          />
          <SourceList
            title={`Research papers (${evidence.papers.total})`}
            items={evidence.papers.most_relevant.slice(0, 3).map((p) => ({ text: `${p.title} (${p.year})`, url: p.url }))}
          />
          {evidence.local.startups.length ? (
            <p>
              Tamil Nadu startups:{" "}
              {evidence.local.startups.map((s) => `${s.name} (${s.district})`).join(", ")}
            </p>
          ) : null}
          {notSearched.length ? (
            <p>
              Not searched:{" "}
              {notSearched.map((c) => `${c.source} (${c.note || c.status})`).join("; ")}
            </p>
          ) : null}
          <p>
            <small>{evidence.caveat}</small>
          </p>
        </details>
      ) : null}
    </section>
  );
}

function SourceList({ title, items }: { title: string; items: Array<{ text: string; url: string }> }) {
  if (!items.length) return null;
  return (
    <>
      <p>{title}</p>
      <ul>
        {items.map((it, i) => (
          <li key={i}>
            {it.url ? (
              <a href={it.url} target="_blank" rel="noreferrer">
                {it.text}
              </a>
            ) : (
              it.text
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
