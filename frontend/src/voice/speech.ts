/* Listening with the browser's own recognition (build spec 1.1–1.5). The
 * mentor's voice is never the browser's: it comes from the server (mentorVoice.ts).
 *
 * Listener: streaming recognition. A turn ends after 700 ms of silence, or
 * 1,200 ms when the last word is a joiner or filler ("and", "so", "um",
 * "athu"), so founders are not cut off while they think.
 *
 * Audio never leaves the browser through Vanigam: the browser's recognition
 * service handles it (in Chrome that is Google's), and only text reaches the
 * backend. The page says so before the microphone is first used.
 */

type Rec = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: RecEvent) => void) | null;
  onspeechstart: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};
type RecEvent = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string; confidence: number } }>;
};

const RecCtor: (new () => Rec) | undefined =
  typeof window !== "undefined"
    ? ((window as unknown as { SpeechRecognition?: new () => Rec }).SpeechRecognition ??
      (window as unknown as { webkitSpeechRecognition?: new () => Rec }).webkitSpeechRecognition)
    : undefined;

export const canListen = Boolean(RecCtor);

const TRAILING = /\b(and|so|but|because|um+|uh+|like|then|athu|apram|ana)\s*$/i;
export const SILENCE_MS = 700;
export const SILENCE_LONG_MS = 1200;

/** How long to wait after the last words before ending the founder's turn. */
export function silenceFor(text: string): number {
  return TRAILING.test(text.trim()) ? SILENCE_LONG_MS : SILENCE_MS;
}

export interface ListenerEvents {
  onPartial: (text: string) => void;
  onFinal: (text: string) => void;
  onSpeechStart: () => void;
  onError: (message: string) => void;
}

export class Listener {
  private rec: Rec | null = null;
  private active = false;
  private finals = "";
  private interim = "";
  private timer: number | undefined;

  constructor(
    private ev: ListenerEvents,
    public lang = "en-IN",
  ) {}

  start() {
    if (!RecCtor || this.active) return;
    this.active = true;
    this.open();
  }

  stop() {
    this.active = false;
    window.clearTimeout(this.timer);
    this.rec?.abort();
    this.rec = null;
    this.finals = this.interim = "";
  }

  setLang(lang: string) {
    this.lang = lang;
    if (this.active) {
      this.rec?.abort(); // reopens in the new language from onend
    }
  }

  private open() {
    if (!RecCtor) return;
    const rec = new RecCtor();
    rec.lang = this.lang;
    rec.continuous = true;
    rec.interimResults = true;
    rec.onspeechstart = () => this.ev.onSpeechStart();
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) this.finals += `${r[0].transcript} `;
        else interim += r[0].transcript;
      }
      this.interim = interim;
      const said = `${this.finals}${interim}`.trim();
      this.ev.onPartial(said);
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => this.flush(), silenceFor(said));
    };
    rec.onerror = (e) => {
      if (e.error === "no-speech" || e.error === "aborted") return;
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        this.active = false;
        this.ev.onError("The microphone is blocked. Allow it in the browser, or type instead.");
      } else {
        this.ev.onError(`Speech recognition stopped (${e.error}). You can keep typing.`);
      }
    };
    rec.onend = () => {
      // Browsers end recognition after a while on their own: reopen while listening.
      if (this.active) window.setTimeout(() => this.active && this.open(), 150);
    };
    this.rec = rec;
    try {
      rec.start();
    } catch {
      /* already started */
    }
  }

  private flush() {
    const said = `${this.finals}${this.interim}`.trim();
    this.finals = this.interim = "";
    if (said) this.ev.onFinal(said);
  }
}

export interface SpeakerEvents {
  onStart: () => void;
  onEnd: () => void; // the queue is empty and nothing is playing
  onPulse: (level: number) => void; // 0..1 for the orb
}

/** True when what the microphone heard is the founder, not our own voice echoing back. */
export function isBargeIn(heard: string, speaking: string): boolean {
  const words = heard.toLowerCase().match(/[\p{L}\p{N}']+/gu) ?? [];
  if (words.length < 3) return false;
  const ours = new Set(speaking.toLowerCase().match(/[\p{L}\p{N}']+/gu) ?? []);
  const foreign = words.filter((w) => !ours.has(w)).length;
  return foreign / words.length > 0.5;
}

/** Microphone level 0..1 for the orb while listening; returns a stop function. */
export async function micLevel(onLevel: (level: number) => void): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true },
  });
  const ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const buf = new Uint8Array(analyser.fftSize);
  let raf = 0;
  const tick = () => {
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) sum += ((v - 128) / 128) ** 2;
    onLevel(Math.min(1, Math.sqrt(sum / buf.length) * 4));
    raf = requestAnimationFrame(tick);
  };
  tick();
  return () => {
    cancelAnimationFrame(raf);
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
  };
}
