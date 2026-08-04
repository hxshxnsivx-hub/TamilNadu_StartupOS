# UI Reference & Hybrid Decisions

Reference set for the Vanigam landing/home UI, and what we take from each.

> **Honesty note.** These are durable *patterns* associated with each product,
> from working knowledge — not a live audit. Marketing sites are redesigned
> often, so treat the named exemplar as "where this pattern was done well",
> not "what that URL shows today". Every pattern below is judged on whether it
> survives contact with our constraints, not on novelty.

---

## A. Landing / home page architecture

| # | Pattern | Exemplar | Take? | Why |
|---|---|---|---|---|
| A1 | **Above-fold contract**: one claim, one proof, one action, nothing else | Linear, Stripe | ✅ | Founders arrive uncertain; a single claim beats a feature list |
| A2 | **Bento panel grid** — unequal tiles, each one idea, scannable in a glance | Apple product pages, Vercel | ✅ | Directly answers "panels organization / space utilisation" |
| A3 | **Progressive disclosure by scroll** — depth revealed in bands | Stripe, Framer | ✅ | Matches our four-chapter model |
| A4 | **Live product surface** instead of a screenshot | Linear, Raycast | ⚠️ partial | We have real endpoints — show a real result, not a mock |
| A5 | **Logo wall / social proof** | almost all SaaS | ❌ | We have no customers yet. Fabricating them is worse than omitting |
| A6 | **Numbers as proof** — big figures, tabular, animated once | Stripe | ✅ | We have honest numbers (8 schemes, 6 axes, 3 languages) |

## B. Background as an active palette

The specific ask: *use the background space itself as the palette, with running
animation.* This is the highest-leverage item — most of a landing page is
background, and leaving it inert wastes the majority of the canvas.

| # | Pattern | Exemplar | Take? | Why |
|---|---|---|---|---|
| B1 | **Aurora / mesh gradient field**, slow drift, very low contrast | Stripe, Vercel, Arc | ✅ | The single best "background as palette" device |
| B2 | **Scroll-reactive hue** — the field retints as sections pass | Apple, Arc | ✅ | Turns scroll into narrative; costs one CSS variable |
| B3 | **Pointer-reactive light** — a soft spotlight follows the cursor | Linear, Vercel | ✅ | Makes the page feel alive without ornament |
| B4 | **Grain / noise overlay** to stop gradients banding | Stripe, Rauno | ✅ | Cheap, and fixes real banding on wide gradients |
| B5 | **Full-bleed video / WebGL** | Apple, awwwards winners | ❌ | Weight and battery cost; wrong for 2G-capable TN users |
| B6 | **Parallax layers** | many | ⚠️ minimal | Nauseating at scale; only a few px of offset |

## C. Motion & hooks

| # | Pattern | Exemplar | Take? | Why |
|---|---|---|---|---|
| C1 | **Scroll-progress-linked** transforms (not just fire-once triggers) | Apple, Framer | ✅ | This is the "hook" the brief is asking for |
| C2 | **Sticky/pinned section** while inner content advances | Apple | ✅ | Buys narrative time without page length |
| C3 | **Masked line-by-line type reveal** | Linear, Vercel | ✅ | Already built (`SetLines`) |
| C4 | **Magnetic / cursor-aware controls** | Awwwards, Igloo | ✅ | Already built (`Magnetic`) |
| C5 | **Number roll-up on view** | Stripe | ✅ | Already built (`Figure`) |
| C6 | **Scroll-jacking / custom smooth scroll** (Lenis etc.) | many agency sites | ❌ | Breaks native scroll, accessibility, and find-in-page |

## D. Density — "efficient time and space utilisation"

| # | Rule | Source of the idea |
|---|---|---|
| D1 | Kill dead vertical space: hero ≤ ~85vh, not 100vh+ | Linear |
| D2 | Every band must carry new information — no decorative filler bands | Stripe |
| D3 | Bento tiles earn their area: bigger tile = more important claim | Apple |
| D4 | One idea per panel, headline readable in < 2 seconds | Vercel |
| D5 | Fold the four chapters into the *same* grid as the proof numbers | ours |

---

## The hybrid

We keep the **Meridian** editorial system (alabaster ground, warm ink, bottle
green, brass) and the **Tamil art layer** (Athangudi rhombille, kolam, korvai,
hara, segmental arch, Paniker cordon), and add three things from the references:

1. **`AuroraField`** — a living background that *is* the palette (B1+B2+B3+B4).
   Three drifting wells in the project's own pigments, a pointer-tracked
   light, and grain over the top. It retints per section as you scroll, so the
   background does narrative work instead of sitting inert.

2. **`BentoGrid`** — the four chapters and the proof numbers share one
   asymmetric grid (A2+D3+D5). Unequal tiles, each a single idea, no filler.

3. **Scroll-progress hooks** — `useScrollProgress` drives real transforms
   rather than one-shot reveals (C1), with a pinned band (C2).

**Deliberately refused:** logo walls (A5 — no customers), WebGL/video (B5 —
weight), scroll-jacking (C6 — accessibility). Each of those would look more
"premium" in a screenshot and be worse in use.
