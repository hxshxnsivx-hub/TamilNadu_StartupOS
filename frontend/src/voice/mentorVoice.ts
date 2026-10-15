/* The mentor's voice, always from Vanigam's server (never the browser's own):
 * Sarvam AI when it has a key, else Gemini's free voice, else the phrasebook of
 * fixed sentences recorded once with a free local voice. A sentence the server
 * has no audio for is shown, not spoken.
 *
 * Latency and quota, by design:
 *  - the first sentence of a reply is requested the moment it arrives, so the
 *    mentor starts speaking at once;
 *  - with Gemini or Sarvam, the sentences that follow while it speaks are joined
 *    into one request (fewer requests on a free quota, the same natural flow);
 *    the phrasebook matches single sentences, so it gets them one by one;
 *  - each request goes out as soon as its text is ready, so the next audio is
 *    ready while the current one plays;
 *  - the moment the founder stops speaking, a short acknowledgement ("சரி.",
 *    "अच्छा।", "Okay.") plays from cache while the words are transcribed and
 *    the reply is prepared: no dead air.
 */

import { speakAudio, transcribe, type Lang } from "./agentClient";
import type { ListenerEvents, SpeakerEvents } from "./speech";

const ACKS: Record<Lang, string[]> = {
  "ta-IN": ["சரி.", "ம்ம், சரி."],
  "hi-IN": ["अच्छा।", "हाँ, ठीक है।"],
  "en-IN": ["Okay.", "Mm, I see."],
};

// Sentence ends as the server splits them (app/agents/grounding.py), so that a
// fixed sentence inside a longer reply still matches its recording.
const SENTENCE_END = /(?<!\b(?:Dr|Rs|Mr|Ms|vs))[.!?।॥](?=\s|$)/g;

export function sentences(text: string): string[] {
  const out: string[] = [];
  let from = 0;
  for (const m of text.matchAll(SENTENCE_END)) {
    const end = (m.index ?? 0) + 1;
    out.push(text.slice(from, end).trim());
    from = end;
  }
  out.push(text.slice(from).trim());
  return out.filter(Boolean);
}

const GROUP_CHARS = 260; // send a group once it is this long
const GROUP_WAIT_MS = 400; // or once no sentence has come for this long

let sharedCtx: AudioContext | null = null;
function audioContext(): AudioContext {
  sharedCtx ??= new AudioContext();
  if (sharedCtx.state === "suspended") void sharedCtx.resume();
  return sharedCtx;
}

export class AudioSpeaker {
  language: Lang = "en-IN";
  current = "";
  private queue: Array<{ text: string; language: Lang; audio: Promise<Blob | null> }> = [];
  private held: { text: string[]; language: Lang } | null = null;
  private holdTimer = 0;
  private busy = false;
  private gen = 0;
  private el = new Audio();
  private analyser: AnalyserNode | null = null;
  private raf = 0;

  /** `group`: join the sentences that follow the first into fewer requests. */
  constructor(
    private ev: SpeakerEvents,
    private group = false,
  ) {}

  get speaking() {
    return this.busy;
  }

  /** Queue text sentence by sentence. The first goes at once; with grouping on,
   * later ones wait briefly to travel together. */
  say(text: string, language: Lang = this.language) {
    for (const sentence of sentences(text)) {
      const idle = !this.busy && this.queue.length === 0 && !this.held;
      if (!this.group || idle) {
        this.enqueue(sentence, language);
        continue;
      }
      if (this.held && this.held.language !== language) this.flush();
      this.held ??= { text: [], language };
      this.held.text.push(sentence);
      window.clearTimeout(this.holdTimer);
      if (this.held.text.join(" ").length >= GROUP_CHARS) this.flush();
      else this.holdTimer = window.setTimeout(() => this.flush(), GROUP_WAIT_MS);
    }
  }

  /** Send whatever is waiting to be grouped (the reply has ended). */
  flush() {
    window.clearTimeout(this.holdTimer);
    const held = this.held;
    this.held = null;
    if (held) this.enqueue(held.text.join(" "), held.language);
  }

  private enqueue(text: string, language: Lang) {
    this.queue.push({ text, language, audio: speakAudio(text, language).catch(() => null) });
    if (!this.busy) void this.next();
  }

  /** A short acknowledgement in the founder's language, played at once. */
  acknowledge(language: Lang) {
    const options = ACKS[language];
    this.say(options[Math.floor(Math.random() * options.length)], language);
  }

  /** Fetch the acknowledgements once, so the server caches them before they are needed. */
  warm(languages: Lang[]) {
    for (const l of languages) for (const a of ACKS[l]) void speakAudio(a, l).catch(() => null);
  }

  cancel() {
    this.gen++;
    this.queue = [];
    window.clearTimeout(this.holdTimer);
    this.held = null;
    this.el.pause();
    this.el.removeAttribute("src");
    cancelAnimationFrame(this.raf);
    this.ev.onPulse(0);
    if (this.busy) {
      this.busy = false;
      this.current = "";
      this.ev.onEnd();
    }
  }

  private async next() {
    if (!this.queue.length && this.held) this.flush(); // never pause for a timer
    const item = this.queue.shift();
    if (!item) {
      this.busy = false;
      this.current = "";
      cancelAnimationFrame(this.raf);
      this.ev.onPulse(0);
      this.ev.onEnd();
      return;
    }
    if (!this.busy) this.ev.onStart();
    this.busy = true;
    this.current = item.text;
    const gen = this.gen;
    const blob = await item.audio;
    if (gen !== this.gen) return; // cancelled while waiting
    if (!blob) {
      // no voice for this now (quota used up, offline): the words are on screen
      window.setTimeout(() => gen === this.gen && void this.next(), 150);
      return;
    }
    const url = URL.createObjectURL(blob);
    this.el.src = url;
    this.el.onended = () => {
      URL.revokeObjectURL(url);
      if (gen === this.gen) void this.next();
    };
    this.meter();
    try {
      await this.el.play();
    } catch {
      URL.revokeObjectURL(url);
      if (gen === this.gen) void this.next();
    }
  }

  private meter() {
    try {
      if (!this.analyser) {
        const ctx = audioContext();
        this.analyser = ctx.createAnalyser();
        this.analyser.fftSize = 256;
        ctx.createMediaElementSource(this.el).connect(this.analyser);
        this.analyser.connect(ctx.destination);
      }
    } catch {
      return; // no level meter: audio still plays
    }
    const a = this.analyser;
    const buf = new Uint8Array(a.fftSize);
    cancelAnimationFrame(this.raf);
    const tick = () => {
      a.getByteTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += ((v - 128) / 128) ** 2;
      this.ev.onPulse(Math.min(1, Math.sqrt(sum / buf.length) * 5));
      this.raf = requestAnimationFrame(tick);
    };
    tick();
  }
}

export interface RecordingEvents extends ListenerEvents {
  onLevel: (level: number) => void;
  onUtteranceEnd: () => void; // the founder stopped: time to acknowledge
  onFinalLang: (text: string, language: Lang) => void;
}

const SPEECH_START_MS = 120; // above the threshold this long = speech
const BARGE_IN_MS = 280; // longer while the mentor is speaking, to ignore echoes
const SILENCE_END_MS = 800; // this much quiet ends the founder's turn
const MIN_UTTERANCE_MS = 350; // shorter is a cough or a click
const MAX_UTTERANCE_MS = 25000; // the service's request limit is about 30 s

function recorderType(): string | undefined {
  const types = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t));
}

/** Records one utterance at a time, cut by a voice-activity detector, and transcribes it. */
export class RecordingListener {
  lang: Lang | "auto" = "auto";
  private stream: MediaStream | null = null;
  private analyser: AnalyserNode | null = null;
  private raf = 0;
  private recorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private floor = 0.01;
  private aboveSince = 0;
  private lastVoice = 0;
  private startedAt = 0;
  private active = false;

  constructor(
    private ev: RecordingEvents,
    private mentorSpeaking: () => boolean,
  ) {}

  setLang(lang: string) {
    this.lang = (["ta-IN", "en-IN", "hi-IN"].includes(lang) ? lang : "auto") as Lang | "auto";
  }

  async start() {
    if (this.active) return;
    if (!navigator.mediaDevices?.getUserMedia || !recorderType()) {
      this.ev.onError("This browser cannot record audio. Type instead.");
      return;
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch {
      this.ev.onError("The microphone is blocked. Allow it in the browser, or type instead.");
      return;
    }
    const ctx = audioContext();
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 512;
    ctx.createMediaStreamSource(this.stream).connect(this.analyser);
    this.active = true;
    this.loop();
  }

  stop() {
    this.active = false;
    cancelAnimationFrame(this.raf);
    if (this.recorder && this.recorder.state !== "inactive") {
      this.recorder.onstop = null;
      this.recorder.stop();
    }
    this.recorder = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.ev.onLevel(0);
  }

  private loop() {
    const a = this.analyser;
    if (!a) return;
    const buf = new Uint8Array(a.fftSize);
    const tick = () => {
      if (!this.active) return;
      a.getByteTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += ((v - 128) / 128) ** 2;
      const rms = Math.sqrt(sum / buf.length);
      this.ev.onLevel(Math.min(1, rms * 4));
      this.step(rms, performance.now());
      this.raf = requestAnimationFrame(tick);
    };
    tick();
  }

  private step(rms: number, now: number) {
    const recording = this.recorder !== null;
    const threshold = Math.max(0.02, this.floor * 3) * (this.mentorSpeaking() ? 2 : 1);
    if (!recording) this.floor = this.floor * 0.98 + Math.min(rms, 0.05) * 0.02; // adapt to the room
    if (rms > threshold) {
      this.lastVoice = now;
      if (!this.aboveSince) this.aboveSince = now;
      const needed = this.mentorSpeaking() ? BARGE_IN_MS : SPEECH_START_MS;
      if (!recording && now - this.aboveSince >= needed) this.begin(now);
    } else {
      this.aboveSince = 0;
    }
    if (recording) {
      const quiet = now - this.lastVoice;
      if (quiet >= SILENCE_END_MS || now - this.startedAt >= MAX_UTTERANCE_MS) this.end(now);
    }
  }

  private begin(now: number) {
    if (!this.stream) return;
    const type = recorderType();
    this.chunks = [];
    this.startedAt = now;
    const rec = new MediaRecorder(this.stream, type ? { mimeType: type } : undefined);
    rec.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    rec.start(100);
    this.recorder = rec;
    this.ev.onSpeechStart();
    this.ev.onPartial("…");
  }

  private end(now: number) {
    const rec = this.recorder;
    if (!rec) return;
    this.recorder = null;
    const long = now - this.startedAt - SILENCE_END_MS >= MIN_UTTERANCE_MS;
    rec.onstop = () => {
      const blob = new Blob(this.chunks, { type: rec.mimeType || "audio/webm" });
      this.chunks = [];
      if (!long || blob.size < 1000) {
        this.ev.onPartial("");
        return; // a cough or a click
      }
      this.ev.onUtteranceEnd();
      this.ev.onPartial("Got it…");
      transcribe(blob, this.lang)
        .then((r) => {
          this.ev.onPartial("");
          if (r.text) this.ev.onFinalLang(r.text, r.language);
        })
        .catch((e: Error) => {
          this.ev.onPartial("");
          this.ev.onError(`I couldn't hear that clearly (${e.message}). Please say it again or type.`);
        });
    };
    rec.stop();
  }
}
