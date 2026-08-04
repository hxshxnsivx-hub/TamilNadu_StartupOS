/* Story layer.
   Each chapter of the founder's journey owns a hue. Moving through the app
   retints the ambient room, so navigation reads as a story rather than a
   palette swap — and gives the reader a wayfinding cue below the level of
   conscious attention. Hues are HSL triplets so CSS can compose alpha. */

import { useEffect } from "react";

export type Chapter = {
  /** HSL triplet for --ambient-1 */
  hue: string;
  /** ordinal, used to decide which way a page slides in */
  order: number;
  /** which of the mural cast presides over this chapter */
  figure: "Sower" | "Weaver" | "Trader" | "Treasurer";
  label: string;
};

export const CHAPTERS: Record<string, Chapter> = {
  "/": { hue: "41 55% 55%", order: 0, figure: "Sower", label: "வணிகம்" },
  "/ideate": { hue: "162 56% 42%", order: 1, figure: "Sower", label: "Ideation" },
  "/schemes": { hue: "222 62% 60%", order: 2, figure: "Weaver", label: "Schemes" },
  "/b2b": { hue: "350 62% 52%", order: 3, figure: "Trader", label: "Collaboration" },
  "/funding": { hue: "41 62% 55%", order: 4, figure: "Treasurer", label: "Funding" },
  "/app": { hue: "41 55% 55%", order: 5, figure: "Treasurer", label: "Home" },
  "/profile": { hue: "28 45% 52%", order: 6, figure: "Weaver", label: "Profile" },
  "/login": { hue: "260 40% 58%", order: 7, figure: "Sower", label: "Enter" },
  "/register": { hue: "260 40% 58%", order: 8, figure: "Sower", label: "Enter" },
};

export const FALLBACK: Chapter = CHAPTERS["/"];

export function chapterFor(pathname: string): Chapter {
  return CHAPTERS[pathname] ?? FALLBACK;
}

/** Retints the ambient room for the active chapter, and records travel
    direction so the page can slide in from the side you came from. */
export function useChapter(pathname: string): Chapter {
  const chapter = chapterFor(pathname);

  useEffect(() => {
    const root = document.documentElement;
    const prev = Number(root.dataset.chapterOrder ?? chapter.order);
    root.style.setProperty("--ambient-1", chapter.hue);
    root.dataset.chapterOrder = String(chapter.order);
    root.dataset.dir = chapter.order >= prev ? "fwd" : "back";
  }, [chapter.hue, chapter.order]);

  return chapter;
}
