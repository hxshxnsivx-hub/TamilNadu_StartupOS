/* Ornamental layer for "Gilded Pigment".
   Pure inline SVG, fixed behind the content, aria-hidden. All motion is CSS
   (see luxe.css) so reduced-motion readers get a still, composed backdrop. */

import { KolamRail } from "./Mural";

const DUST = [
  [6, 18, 2.0, 0],
  [14, 74, 1.3, 3.1],
  [23, 41, 1.7, 6.4],
  [31, 88, 1.1, 1.7],
  [39, 26, 2.2, 8.2],
  [47, 63, 1.4, 4.5],
  [55, 12, 1.8, 10.1],
  [63, 79, 1.2, 2.3],
  [71, 35, 2.0, 7.0],
  [79, 68, 1.5, 5.2],
  [86, 22, 1.9, 9.4],
  [93, 55, 1.3, 3.8],
] as const;

/** Fixed, full-bleed gilded backdrop: mesh light, gold dust, corner filigree.
    The first wash follows --ambient-1, so the room retints per chapter. */
export function LuxeBackdrop() {
  return (
    <div className="lx-backdrop" aria-hidden="true">
      {/* the domain's own material, half off-canvas — not a generic shape */}
      <div className="lx-glyph">வணிகம்</div>
      <KolamRail className="lx-rail" />

      <svg
        className="lx-mesh"
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid slice"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <radialGradient id="lx-g1" cx="18%" cy="12%" r="58%">
            <stop offset="0%" stopColor="hsl(var(--ambient-1))" stopOpacity="0.34" />
            <stop offset="100%" stopColor="hsl(var(--ambient-1))" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="lx-g2" cx="86%" cy="24%" r="52%">
            <stop offset="0%" stopColor="var(--ochre)" stopOpacity="0.26" />
            <stop offset="100%" stopColor="var(--ochre)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="lx-g3" cx="60%" cy="94%" r="62%">
            <stop offset="0%" stopColor="var(--jade)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--jade)" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="lx-gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--gold-pale)" />
            <stop offset="50%" stopColor="var(--ochre)" />
            <stop offset="100%" stopColor="var(--ochre-deep)" />
          </linearGradient>
        </defs>
        <rect width="100" height="100" fill="url(#lx-g1)" className="lx-blob lx-b1" />
        <rect width="100" height="100" fill="url(#lx-g2)" className="lx-blob lx-b2" />
        <rect width="100" height="100" fill="url(#lx-g3)" className="lx-blob lx-b3" />
      </svg>

      {/* gold dust, drifting upward at different rates */}
      <svg className="lx-dust" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {DUST.map(([x, y, r, d], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={r / 10}
            fill="var(--ochre)"
            className="lx-mote"
            style={{ animationDelay: `${d}s` }}
          />
        ))}
      </svg>

      <Filigree className="lx-fil lx-fil-tl" />
      <Filigree className="lx-fil lx-fil-br" />
    </div>
  );
}

/** A corner flourish — temple bracket geometry, drawn in gold. */
function Filigree({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M2 2h44M2 2v44M2 26c22 0 46 6 60 22M26 2c0 22 6 46 22 60"
        stroke="url(#lx-gold)"
        strokeWidth="0.9"
        strokeLinecap="round"
        opacity="0.5"
      />
      <path
        d="M10 10c14 2 30 10 40 22M10 10c2 14 10 30 22 40"
        stroke="var(--ochre-deep)"
        strokeWidth="0.6"
        strokeLinecap="round"
        opacity="0.4"
      />
      <circle cx="2" cy="2" r="2.6" fill="var(--ochre)" opacity="0.55" />
    </svg>
  );
}

/** An ornamental rule: gold hairline through a small diamond. */
export function Divider() {
  return (
    <div className="lx-divider" aria-hidden="true">
      <span className="lx-div-rule" />
      <svg viewBox="0 0 24 24" className="lx-div-mark" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M12 2l4 10-4 10-4-10z"
          fill="none"
          stroke="var(--ochre)"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
        <circle cx="12" cy="12" r="1.6" fill="var(--gold-pale)" />
      </svg>
      <span className="lx-div-rule" />
    </div>
  );
}
