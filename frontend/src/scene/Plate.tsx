/* Full-bleed photographic band — the reference's second signature move.
 *
 * In the clip, sections like "Horology" are a full-bleed photograph with the
 * title set bottom-left over it and a mono chapter mark above. The image is
 * not decoration behind a card; it IS the section.
 *
 * The photograph drifts slowly against the scroll (a slow ken-burns push), so
 * the band feels alive without competing with the copy sitting on it.
 *
 * Swapping the image is one prop. Drop a file in public/scene/ and pass its
 * name — nothing else changes.
 */

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

const REDUCED =
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function Plate({
  src,
  n,
  eyebrow,
  title,
  lede,
  children,
  align = "left",
  height = "82vh",
}: {
  /** file in /public/scene, e.g. "bank.jpg" */
  src: string;
  /** chapter number, e.g. "02" */
  n?: string;
  eyebrow?: string;
  title: string;
  lede?: ReactNode;
  children?: ReactNode;
  align?: "left" | "right";
  height?: string;
}) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (REDUCED) return;
    const el = ref.current;
    if (!el) return;
    // -1 above the viewport … 0 centred … +1 below. Drives a gentle push.
    const update = () => {
      const r = el.getBoundingClientRect();
      const mid = r.top + r.height / 2;
      const t = (mid - window.innerHeight / 2) / (window.innerHeight + r.height);
      el.style.setProperty("--t", Math.max(-1, Math.min(1, t * 2)).toFixed(4));
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [src]);

  return (
    <section
      className={`pl pl-${align}`}
      ref={ref}
      style={{ "--img": `url(/scene/${src})`, "--h": height } as CSSProperties}
    >
      <div className="pl-img" aria-hidden="true" />
      <div className="pl-grade" aria-hidden="true" />
      <div className="pl-body">
        {(n || eyebrow) && (
          <div className="pl-mark">
            {n && <span>{`{ ${n}${eyebrow ? " · " + eyebrow.toUpperCase() : ""} }`}</span>}
          </div>
        )}
        <h2 className="pl-t">
          {title.split("\n").map((line, i) => (
            <span key={i}>{line}</span>
          ))}
        </h2>
        {lede && <p className="pl-lede">{lede}</p>}
        {children}
      </div>
    </section>
  );
}
