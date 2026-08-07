/**
 * AmbientBackground — the layer that claims the dead gutters.
 *
 * Ported from Bharath-tax-mitra, whose version was the best single idea in
 * that project: not a generic gradient wash, but ambient drawn from the
 * subject's own world. Theirs used a giant ₹ glyph and a rail stepped like
 * India's tax slabs. Ours uses:
 *
 *   வ  the first letter of வணிகம் — the product's own initial, engraved in
 *      gold outline, half off-canvas so it reads as architecture rather
 *      than as a watermark
 *   ▁▂▃ a rail that TAPERS UPWARD like a gopuram tier — Tamil Nadu's temple
 *      towers step inward as they rise, which is why the widths decrease
 *      toward the top rather than increasing (the tax-slab version stepped
 *      the other way, and copying it unexamined would have been wrong)
 *   ○  two very slowly drifting orbs, gold and jade
 *   ░  the grain film that stops near-black reading as a switched-off screen
 *
 * Per-route accent hue via --ambient-1, so moving through the product reads
 * as chapters rather than as a palette swap.
 *
 * Constraints: fixed, z-0 (behind .app's z-1, above .wall's z-0 by DOM
 * order), pointer-events-none, aria-hidden — never intercepts input, never
 * enters the a11y tree, never affects layout. Transform/opacity animation
 * only, neutralised by nocturne's global reduced-motion kill switch.
 * Opacities stay low enough that foreground contrast is untouched.
 */

import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/* Gopuram tiers: widest at the base, tapering as it rises. */
const TIERS = [
  { w: "w-44", o: 0.13 },
  { w: "w-32", o: 0.11 },
  { w: "w-24", o: 0.09 },
  { w: "w-16", o: 0.07 },
  { w: "w-10", o: 0.05 },
];

/* Route hues follow the Tamil colour names already used for the Home
   chapters, so the ambient and the content agree about where you are. */
const ROUTE_HUES: Record<string, string> = {
  "/": "41 55% 55%", // gold — the default ground
  "/ideate": "185 55% 45%", // mayil · peacock
  "/schemes": "355 50% 50%", // arakku · lac
  "/b2b": "95 40% 45%", // manthulir · mango leaf
  "/supply": "95 40% 45%",
  "/funding": "38 55% 50%", // brass
  "/pipeline": "38 55% 50%",
  "/intel": "220 45% 55%",
};

/** Retunes --ambient-1 to match the active route. */
function useAmbientHue() {
  const { pathname } = useLocation();
  useEffect(() => {
    const hue = ROUTE_HUES[pathname] ?? "41 55% 55%";
    document.documentElement.style.setProperty("--ambient-1", hue);
    return () => {
      document.documentElement.style.removeProperty("--ambient-1");
    };
  }, [pathname]);
}

export default function AmbientBackground() {
  useAmbientHue();

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 select-none overflow-hidden">
      {/* Orbs — accent follows the route, the second stays constant */}
      <div
        className="animate-ambient absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full blur-3xl transition-colors duration-700"
        style={{ backgroundColor: "hsl(var(--ambient-1) / 0.10)" }}
      />
      <div
        className="animate-ambient-delayed absolute -bottom-48 -right-32 h-[38rem] w-[38rem] rounded-full blur-3xl"
        style={{ backgroundColor: "hsl(var(--ambient-2) / 0.07)" }}
      />

      {/* வ — engraved gold outline, half off-canvas right */}
      <div
        lang="ta"
        className="absolute -right-24 top-1/2 -translate-y-1/2 rotate-6 font-tamil font-black leading-none"
        style={{
          fontSize: "clamp(18rem, 42vw, 34rem)",
          color: "transparent",
          WebkitTextStroke: "2px hsl(var(--gold) / 0.14)",
        }}
      >
        வ
      </div>

      {/* Grain film — the material layer */}
      <div className="texture-grain absolute inset-0 opacity-[0.06]" />

      {/* Gopuram rail — desktop gutters only, tapering upward.
          flex-col-REVERSE is load-bearing: TIERS is ordered widest-first, so
          reversing puts the widest band at the base. Plain flex-col would
          render an inverted pyramid. */}
      <div className="absolute bottom-0 left-0 hidden flex-col-reverse gap-1.5 pb-10 lg:flex">
        {TIERS.map((tier, i) => (
          <div
            key={i}
            className={`${tier.w} h-2.5 rounded-r-full transition-colors duration-700`}
            style={{ backgroundColor: `hsl(var(--ambient-1) / ${tier.o})` }}
          />
        ))}
      </div>
    </div>
  );
}
