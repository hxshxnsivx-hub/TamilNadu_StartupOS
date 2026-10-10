import "./orb.css";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

const LABEL: Record<OrbState, string> = {
  idle: "Tap to talk",
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Speaking (talk to interrupt)",
};

/** The voice agent's presence: one button, four states, glow follows the voice level. */
export default function Orb({
  state,
  level,
  onToggle,
  disabled,
}: {
  state: OrbState;
  level: number;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <button
        type="button"
        className="vg-orb"
        data-state={state}
        style={{ ["--level" as string]: level.toFixed(3) }}
        onClick={onToggle}
        disabled={disabled}
        aria-pressed={state === "listening"}
        aria-label={state === "listening" ? "Stop listening" : "Start talking"}
      >
        <span className="vg-orb__halo" />
        <span className="vg-orb__body" />
        <span className="vg-orb__swirl" />
      </button>
      <p className="vg-orb__label" aria-live="polite">
        {LABEL[state]}
      </p>
    </div>
  );
}
