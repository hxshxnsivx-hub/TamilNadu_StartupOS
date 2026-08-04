# UI state — handoff

## Current design system — "ATELIER"

Not a reset. MERIDIAN (light editorial: alabaster ground, warm ink, bottle
green, antique brass) is intact and still supplies the theme. ATELIER adds the
parts that were missing — a token layer, a primitive set, and a composed
background — and re-lays every page on them.

**The problem it solves is not decoration, it is density.** Every card in this
product carries the same awkward shape: identity, one or two scores, a
variable-length list of reasons, and a provenance stamp — in Tamil, at 375px,
over 2G. Nine pages were each solving that privately, which is why the app read
as nine products. The card is now solved once and the pages compose it.

### Cascade order (`src/main.tsx`) — load-bearing

| Sheet | Owns |
|---|---|
| `index.css` | base reset; legacy layout still used by NewsBoard |
| `meridian.css` | theme: ground, ink, signal, brass, surfaces, type |
| `meridian-motion.css` | older motion grammar, `ScrollRail`, kolam, NewsBoard |
| `design/tokens.css` | **canonical tokens** — see below |
| `design/wall.css` | the background as a composed surface |
| `design/atelier.css` | structure: the primitives |
| `design/compositions.css` | page-specific arrangements of those primitives |

### The four laws (`design/tokens.css`)

From the sourced research in `art-reference-tn.md` / `art-reference-pondicherry.md`.
These are not stylistic preferences; breaking one is a bug.

1. **Ornament lives at edges, never in the field.**
2. **Repetition with diminution** — nesting scales by a constant (`r ≈ 0.8`
   between bands, `0.93` within one).
3. **Hard colour boundaries.** Exactly two gradients are authorised: shot silk
   (`--shot-*`) and egg-lime plaster satin (`--satin`). Nothing else.
4. **Two chromatic colours per surface**, plus ground and ink.

Plus two that get broken most often in practice:

- **One heavy horizontal per composition** (`--rule-cornice`, max two per page).
  A façade with two heavy horizontals reads as two buildings.
- **No arbitrary `border-radius`.** Four legal values only, the column ladder
  square → octagon → 16-gon → circle: `--corner-0…3`.

### Tokens worth knowing

- **Pigment names are traditional; hex values are screen encodings.** Do not
  cite them as "the traditional colour of X". `--arakku` (lac red, the single
  accent), `--mayil` (peacock's neck), `--manthulir` (tender mango leaf, a shot
  colour), plus the Athangudi oxides as the data tones.
- **Space** — `--court-0…3` is the Chettinad diminishing-courtyard ladder.
  `--space-base/gate/eye/well` is Tamil's four degrees of space; the *gate* (the
  gap between the stems of ர) is the script's rhythm unit and so the UI's.
- **Opacity ceilings** for every ornament layer (`--op-weave`, `--op-hara`,
  `--op-circles`, `--op-disc`, `--op-kolam`). These are ceilings, not starting
  points.
- **Motion** — ambient loops are measured in minutes (`--amb-*`), interface
  motion in milliseconds (`--t-*`). The two never borrow each other's timing.

## Components

| File | Role |
|---|---|
| `src/design/tokens.css` | the canonical token set |
| `src/design/atelier.tsx` | **all primitives** — see table below |
| `src/design/atelier.css` | their structure |
| `src/design/compositions.css` | page-specific arrangements |
| `src/components/Wall.tsx` | the five-layer background + `useWallTone` + `useScrollProgress` |
| `src/design/wall.css` | its layers and loops |
| `src/components/Athangudi.tsx` | rhombille geometry + kolam knot |
| `src/components/NewsBoard.tsx` | unchanged |

### Primitives (`src/design/atelier.tsx`)

`Page` · `Masthead` · `Band` · `Register`/`Cell` · `Plate`/`PlateHead` ·
`Reasons` · `Chips` · `Provenance` · `Dial` · `Meter` · `Stat` · `Shelf` ·
`Cornice` · `Hara` · `FreeRule` · `Setting` · `Uncover` · `Rail`/`RailPanel` ·
`Empty` · `Threshold` · `Waiting` · `Pending` · `Magnetic` · `useCount`

Their provenance, in one line each:

- **Plate** — *korvai*: border and body are different fabrics interlocked at a
  hard edge, ratio 1 : 6. The accent never fades into the card.
- **Register** — Paniker's compartmented field: unequal cells, shared hairlines,
  no gutters, and **one quadrant deliberately left empty**. That emptiness is
  what makes it read as composed rather than filled. This is the bento.
- **Shelf** — *thinnai*, the raised platform at the street edge where the
  merchant actually did business. Primary actions live on it.
- **Hara** — the parapet: kuta – panjara – sala – panjara – kuta, in the sourced
  widths. South Indian without a single figure or deity.
- **Threshold** — the compound wall's one emphatic gateway. **Semicircular**
  arch, because semicircular is for thresholds and segmental is for content.
- **Rail** — story mode; see below.
- **Empty** — rejection *as a roadmap*: a ranked count of what blocked you, each
  paired with the thing that would change it.

## The Wall — background as a built surface

Five layers, all transform/opacity, all perfect loops, none carrying meaning:

1. **pigment wells** — three, on mutually prime periods (37 / 43 / 53 s) so the
   field can never visibly return to a previous state
2. **weave** — the Athangudi rhombille floor. Translating by the pattern tile
   `(s√3, 3s)` is exactly `2b` in lattice terms, so the loop is seamless *by
   construction*, not by a crossfade
3. **circles** — the Auroville amphitheatre's offset concentric family. Because
   `Δc < ΔR` the rings stay nested but eccentric, and that single asymmetry is
   what stops concentric circles reading as a target
4. **discs** — Matrimandir's field: two radii at 1 : 1.53, twice as many small
   as large, the two populations drifting in **opposite** directions
5. **grain** — wide low-contrast gradients band badly on 8-bit displays

Below 560px, layers 3 and 4 are dropped. Under reduced motion everything stops
on its first frame.

`useWallTone` retints per band via `[data-tone]`. **`Page` deliberately carries
no `data-tone`** — it spans the whole document, so tagging it made it win the
centre-line test at every scroll position and the wall never changed. Tone
belongs on the bands.

## Story mode

Two rails ship: the four chapters on Home, and the milestone roadmap on Ideate.
A rail pins a band and moves its track laterally, so *n* panels cost one screen
of height instead of *n*.

**Travel is measured, not derived.** The earlier formula assumed every panel was
exactly `1/count` of the track, which silently under-travels the moment the
panel count and the scroll height differ (a capped roadmap), a panel wraps, or
`clamp()` on panel width resolves differently. `Rail` now reads
`track.scrollWidth − track.clientWidth` and writes `--travel` in px. `count` is
the real panel count; `screens` caps the scroll cost separately.

## Hard-won lessons — do not regress these

**Never let a frame loop be the only thing that makes something correct.** In a
tab that is not painting, rAF never fires and CSS animations never advance.

- Odometer / `useCount` rolls on a `setTimeout`, never rAF. An observer that
  never fires would leave it resting on 0 — a *wrong number*, far worse than a
  right one with no roll.
- `useWallTone` picks whichever section owns the viewport centre line, not an
  IntersectionObserver ratio: a section taller than the shrunk root can never
  reach a high ratio, so the tone would simply never change.
- Scroll progress is written **synchronously** on scroll, not in rAF.
- **Reveals never use `@keyframes … both`.** A keyframe animation with
  fill-mode `both` holds its *from*-state forever if the animation never
  starts — which strands a real scheme card at `opacity: 0`. Reveals use
  transitions, whose end state is a plain declaration.
- **`is-set`** — every reveal primitive stamps this at 2200 ms regardless of
  what happened, and CSS uses it to force the end state with transitions off.
  A legitimate reveal (620 ms + ≤440 ms stagger) is long finished by then, so
  it is invisible on the happy path and a hard guarantee on the failing one.
- **Meter and lock-bar widths come straight from the data and are never
  animated from zero**, for the same reason as the odometer.

## Verified state (2026-08-02)

- `npx tsc --noEmit` clean · `npm run build` ✓ — **287.8 kB JS / 79.0 kB CSS**
  (16.07 kB CSS gzipped; was 74 kB uncompressed before, and that was with three
  page sheets that are now unloaded)
- Zero horizontal overflow on **every** route at both 375px and 1280px
- Live against the running backend:
  - Schemes — 8 eligible plates, dials rolled to 100/94/64/51; forcing a harder
    profile yields 4 eligible + 4 refused, refusal marks render as 9×2px bars in
    `--arakku` (a different **shape** from the eligible dot, so the distinction
    survives greyscale)
  - B2B — 2 supplier plates, dials 95/70, 8 breakdown meters
  - Funding — readiness register (dial 81), 6 investor plates, 8 axis meters
  - Ideate — feasibility register (dial 56), 3 clarification steps, **9-panel
    roadmap rail** over 5 screens, last panel flush at p = 1
- Wall retints through all four tones in order: `base` → `chapters` →
  `statement` → `work`
- Home rail measured: `--p` 0 → 0.5 → 1.0, travel −432px, last panel lands
  exactly on the pin's content edge
- After the `is-set` guarantee: **zero elements left below opacity 1** on any
  route


## The elevation pass — "tasteful → striking"

The system above was *correct* and quiet. This pass was about the gap between
competent and striking, driven by an external reference brief (type foundries,
museums, architecture practices, publishing) rather than by the spec.

### The root cause of "boring", found before any design work

`index.html` downloaded **Archivo Black, Inter, Noto Sans Tamil and JetBrains
Mono** — while `--display` pointed at a Palatino/Georgia *system* stack and
`--mono` at `ui-monospace`. Every heading in the product rendered in **Georgia**,
and two downloaded families were never used at all. The app paid the bytes and
got stock typography.

Fixed: Archivo Black dropped, **Fraunces** added as the real display face, Inter
trimmed 400–700 (800/900 were requested and unused), `--mono` repointed at the
JetBrains Mono that was already being downloaded. Same family count, two dead
downloads removed.

### The typographic move that matters

**Low weight at high optical size.** `--display-huge: "opsz" 144, "SOFT" 0,
"WONK" 1` with `font-weight: 300` turns Fraunces into razor-thin, high-contrast,
Didone-adjacent letterforms at 133px — nothing like the 700-weight Fraunces
everyone else ships. Weight climbs back to 500 below 700px, where the line is
physically small and a hairline stroke would go weak.

Scale went from `clamp(2.9rem, 7.4vw, 6.2rem)` to `clamp(3.1rem, 10.4vw,
9.5rem)`. H1 : body is now ~8.6 : 1 at desktop; it was ~4 : 1.

Three optical sizes, not one: `--display-huge` (144) for statements,
`--display-mid` (72) for band titles, `--display-small` (24) for plate titles.
opsz goes DOWN and weight UP as the setting shrinks — which is what an optical
size axis is actually for.

### Signature devices (`design/signature.css`)

Each is rationed; they stop working when they repeat.

| Device | Rule |
|---|---|
| **Inverted band** | full-bleed `#14120f`, **one per page**, on the band carrying that page's payload |
| **Folio numerals** | roman, vertical, in the gutter; hidden below 1180px |
| **Registration crosshairs** | brass hairlines on the outer corners of a Register only |
| **Drop cap** | lead paragraph only, and **Latin-only by script** — a floated initial slices Tamil and Devanagari matras |
| **Cropped display line** | landing masthead only |
| **Vertical section label** | ultra-tracked mono in the gutter |
| **Figure wall** | brass numerals at `clamp(3.6rem, 9vw, 7.5rem)` on the inverted ground |
| **Colophon** | provenance stated as a printer's colophon |

Where the inversions live: Home (the proof), Ideate (feasibility), Funding
(readiness), Pipeline (metrics), Intel (source counts). **Schemes deliberately
has none** — a ledger of results reads best on paper.

### The ledger grid

`.v-grid` gap is **1px** with the container painted `--hair-2`, so the rules
between results are *revealed* rather than drawn, and plates inside it carry no
border, no radius and no shadow. Cards are what make a product look like every
other product; a ruled register is what makes it look editorial. The korvai
accent edge survives, because that is structure, not decoration.

Corner ladder tightened: `--corner-1` 2px → **0**, `--corner-2` 4px → 2px. A 2px
radius is a hedge — too small to read as soft, big enough to stop an edge being
an edge.

### Two bugs this pass introduced and fixed — same root cause

**Never cross-reference a custom property you are redefining in the same rule.**
Custom properties resolve against the element's *own* computed values.

1. `--ink: var(--paper-2)` inside `.is-invert`, which also overrode `--paper-2`
   → ink and paper both collapsed to `#1c1a16`. The pull quote rendered at
   **1:1 — invisible**.
2. After fixing that, `background: var(--ink)` on the same element resolved to
   the *new* `--ink` (`#faf8f3`) and painted the "inverted" band **alabaster**.

Both now use literal hex. Measured contrast on the `#14120f` ground:
paper-2 17.62 · ink-2 12.42 · ink-3 8.21 · ink-4 5.56. Brass was lifted
`#9a7b45` → `#b8965a` (4.71 → 6.72) because it carries labels there, not just
marks.

### Verified after the elevation

- `tsc` clean · build clean — **320.0 kB JS / 95.2 kB CSS** (18.81 kB gzipped)
- Fraunces, Inter, JetBrains Mono and Noto Sans Tamil all confirmed loaded and
  resolving; `--display` and `--mono` no longer fall back to system stacks
- **Zero contrast failures** — every text node inside every inverted band audited
  against its real painted background at the correct WCAG floor (3:1 large,
  4.5:1 normal), not a hand-picked sample
- Zero horizontal overflow on all 12 routes at **375px and 1280px**
- Display resolves 133px/300 at desktop, 50px/500 at 375px
- Reveal elements are mid-transition at 900 ms and fully resolved by 3100 ms,
  with `is-set` landing — the guarantee holds


### The Tamil clipping bug — caught after the elevation, worth not repeating

Pushing the display scale up broke Tamil, and it broke it *silently*.

`.v-set-line` carries `overflow: hidden` for the reveal mask. So when Tamil
headings exceeded the measure they were **cut mid-word** instead of pushing the
layout — and every overflow check still reported **0**, because the mask
absorbed it. Measured at 375px: `/b2b` over by 125px, `/schemes` by 89px,
`/ideate` by 44px.

Two script-level causes: Tamil is agglutinative (single words like
சப்ளையர்களைக் exceed a 375px measure at display size) and Tamil does not
hyphenate, so there is no break opportunity inside them.

Compounding it: **`<html lang>` was never updated by the language switch.** The
document stayed `lang="en"` regardless, so every `:lang(ta)` rule in the system
was dead — the Tamil type metrics, the script-aware sizing, and the drop cap's
script exclusion. `i18n.on("languageChanged", …)` now sets it.

Rule going forward: **an overflow check that passes is not proof the text fits
when a mask is in play.** Measure `inner.scrollWidth` against
`line.clientWidth`, not `documentElement.scrollWidth`.

### Known content gap

The headings on `/start`, `/supply`, `/pipeline`, `/intel` and `/consent` are
hardcoded English, not i18n keys — they do not translate. Those five screens
were built in this pass and their copy never went into `i18n.ts`.

## Not verified live

`/app` (Dashboard) and `/profile` sit behind real server auth. They were checked
via a temporary unguarded route — markup, all new classes, zero overflow at both
widths, and full opacity resolution — and that route was then removed. They have
**not** been exercised with a real signed-in session.

## Housekeeping the rewrite left behind

These modules are now unreferenced. They were **not deleted**, because
`frontend/` is not tracked by git (`?? frontend/` in `git status`) and deletion
would be unrecoverable. Prune deliberately:

`components/Aurora.tsx` · `story/StoryTrack.tsx` · `story.ts` ·
`components/Facade.tsx` · `components/Ring.tsx` · `components/Motif.tsx` ·
`components/Mural.tsx` · `components/Ornament.tsx` · `components/Procession.tsx` ·
`components/ui/marquee-along-svg-path.tsx` · `lib/utils.ts` · `meridian.tsx` ·
`luxe.css` · `motion.css` · `styles/home.css` · `styles/account.css` ·
`styles/results.css` · `styles/journey.css`

`motion.tsx` is still used, but only for `ScrollRail` and `useStuck`; `Reveal`
and `useCountUp` in it are now dead. The `motion` npm package was only ever used
by `marquee-along-svg-path.tsx` and can go with it.

Large stretches of `index.css` and `meridian-motion.css` are now dead too — the
old page classes (`.scheme`, `.ms`, `.cat`, `.jr-*`, `.rs-*`, `.ac-*`, `.hm-*`).
Only the base reset, `.brand`, `ScrollRail`, the kolam and the `.nb-*` NewsBoard
rules are still reached.

## Running the app

Both servers are in `.claude/launch.json` with `autoPort: false` (the Vite proxy
hardcodes `127.0.0.1:8000`, so the backend cannot move ports).

```
cd frontend && npm run dev          # :5173
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Caveat carried forward

The in-app preview pane does not paint frames — `document.timeline.currentTime`
never advances, `scroll-behavior: smooth` makes scripted scrolling a no-op (use
`behavior: 'instant'`), and CSS transitions freeze mid-flight so
`getComputedStyle` returns the start value. Layout, computed styles, class
landing and **resolved** end states are all verifiable there; the motion itself
is not. Judge animation in a real browser at `http://127.0.0.1:5173`.
