# Art Reference — Puducherry & Modern Tamil Visual Traditions

**Purpose.** Source material for the ornamental and structural language of the Vanigam UI.
This document is a *specification*, not art history. Every section ends with construction
rules precise enough to draw in SVG or CSS.

**Existing palette this must serve:**

| Token | Hex | Role |
|---|---|---|
| `alabaster` | `#f4f1ea` | paper ground |
| `ink` | `#14120f` | warm near-black text |
| `bottle` | `#1d3d33` | deep bottle green |
| `brass` | `#9a7b45` | antique brass accent |

**Explicit exclusion:** no figurative mural characters. Everything below is
architectural, typographic, or abstract mark-making.

---

## Confidence markers — read these

Every non-obvious claim carries a marker. Do not strip them when quoting this file.

| Marker | Meaning |
|---|---|
| **[S]** | **Sourced** — stated in a cited source, quoted or closely paraphrased. |
| **[D]** | **Derived** — mathematics I computed from **[S]** numbers. Verifiable. |
| **[I]** | **Inferred** — typical building/craft practice, *not* a Puducherry-specific survey figure. Usable as a design default; do not cite as fact. |
| **[X]** | **Conflict or gap** — sources disagree, or the figure does not exist publicly. |

### The three biggest honest gaps, stated up front

1. **There is no published INTACH or Government of Puducherry heritage colour code. [X]**
   I read the *Puducherry Building Bye-Laws and Zoning Regulations* (Amendment) text in
   full for heritage/colour clauses. The only aesthetic control is a general one:

   > "(10) Composition: Where several facades constitute architectural composition
   > painting and other treatment shall only be allowed where no aesthetic disfigurement
   > can result to the composition as a whole."

   That is the entire statutory colour provision. No RAL/NCS/Munsell list exists in the
   bye-laws. Sources describe the colours only in words — "sunburnt yellow", "mustard
   yellow", "peach", "white", "grey". **Every hex code in the Puducherry sections below
   is my own calibration of those verbal descriptions against photographs. They are
   design-usable, but they are not official.**

2. **Facade dimensional proportions for Puducherry are reconstructions. [I]**
   INTACH's own published Heritage Trail text names the *elements* (pilaster, cornice,
   segmental arch, louvered shutter, parapet) but publishes **no measurements**. Bay
   widths, pilaster projections and shutter proportions below are marked **[I]**.

3. **Matrimandir sphere height is disputed. [X]** See §3.1.

---

# 1. Puducherry French Quarter — *Ville Blanche*

## 1.1 What it actually looks like

The French quarter grew along the beach and around today's Bharathi Park, on a strict
grid of perpendicular streets laid out after the British razed the town in 1761; a storm
water canal separates it from the Tamil quarter. **[S]** Street façades are **continuous
wall-to-wall construction with high garden walls and elaborate gateways** — you read a
street as one unbroken masonry plane pierced by gates, not as a row of separate houses.
**[S]** The plane is then articulated in two directions: **"The façades are divided into
smaller panels by the use of vertical pilasters and horizontal cornices, and feature flat
or segmental arched windows with bands and louvered wooden shutters."** **[S]** Wooden
balconies sit on iron brackets, and a continuous parapet with simple ornamental features
runs the skyline. **[S]**

The critical adaptation: the Parisian pitched roof was replaced by a **flat terraced
roof**, and the main façade opens onto a **colonnaded portico** facing a private walled
garden court — so the ornate face of the building points *inward*. **[S]** "The interiors
of the houses are usually more ornate than the exterior." **[S]** High ceilings, tall
arched doors and windows, vaulted winding staircases; inclined window shades in light
wood or metal. **[S]** Colours are "primarily sun burnt yellow, peach or white", with
white trim used to pick out the pilasters, bands and cornices against the coloured field.
**[S]**

**Design principle to carry into UI:** *a single continuous plane, subdivided by a
lightweight orthogonal frame, with all richness held behind the frame rather than on it.*

## 1.2 Concrete geometry

### 1.2.1 The panel grid (façade as layout system)

The façade is a rectangular field partitioned by **verticals (pilasters)** and
**horizontals (cornices + string courses)**. This is literally a CSS grid.

```
Vertical rhythm    ──  parapet cap
(top to bottom)    ══  main cornice          <- heaviest horizontal
                   ┆   panel: window head band
                   ┆   panel: window + shutters
                   ┆   panel: sill band
                   ──  string course / floor line
                   ┆   ground storey panel
                   ▂▂  plinth
```

Proportions **[I]** (defaults, not survey data — tune freely):

| Quantity | Value | Notes |
|---|---|---|
| Bay pitch `B` | 1 unit | one window + its flanking wall |
| Window opening width | `0.52 B` | slightly over half the bay |
| Pilaster width | `0.10 B` | |
| Pilaster projection | `0.012 B` | shallow — it is a shadow line, not a column |
| Band (architrave) around opening | `0.045 B` | the "bands" INTACH names **[S]** |
| Main cornice depth | `0.13 B` | the one truly heavy horizontal |
| String course depth | `0.035 B` | |
| Storey height | `1.55 B` | tall rooms **[S]**, hence tall bays |
| Window opening height (segmental head) | `1.05 B` | ratio h:w ≈ 2:1 |

**Rule that matters more than the numbers:** exactly **one** horizontal in the composition
is heavy (the main cornice). Everything else — string courses, bands, sill lines — is a
hairline. A façade with two heavy horizontals reads as two buildings.

CSS translation:

```css
.facade {
  --bay: 220px;
  display: grid;
  grid-template-columns: repeat(auto-fill, var(--bay));
  /* pilaster = the grid gap made visible */
  column-gap: calc(var(--bay) * 0.10);
  background-image: linear-gradient(90deg, var(--pilaster) 0 100%);
}
```

### 1.2.2 Segmental arch — exact construction

INTACH names "flat or segmental arched windows" **[S]**. The segmental arch is the single
most reproducible piece of geometry in the whole quarter.

Given span `S` and rise `r` (with `r < S/2`), the arc is a circle of radius:

```
R = (S²/4 + r²) / (2r)
```

centre on the vertical axis at depth `R − r` **below** the springing line; half-angle
`θ = asin((S/2) / R)`. **[D]**

Precomputed table **[D]** — verified numerically:

| `r/S` | `R` | centre below springing | half-angle | character |
|---|---|---|---|---|
| 1/4 | `0.6250 S` | `0.3750 S` | 53.13° | deep, almost stilted |
| 1/5 | `0.7250 S` | `0.5250 S` | 43.60° | generous |
| **1/6** | **`0.8333 S`** | **`0.6667 S`** | **36.87°** | **the default — use this** |
| 1/8 | `1.0625 S` | `0.9375 S` | 28.07° | very shallow, modern |

`r/S = 1/6` is exact and memorable: **`R = 5S/6`, centre at `2S/3` below the springing,
half-angle 36.87°** — a clean 3-4-5 triangle. (`r/S = 1/4` is also a 3-4-5, at 53.13°.)

SVG, springing line at `y = 0`, arch bulging upward (y-down coordinates):

```svg
<!-- span S=100, rise S/6 -> R = 83.333 -->
<path d="M 0 0 A 83.333 83.333 0 0 1 100 0" fill="none" stroke="currentColor"/>
```

Semicircular version — INTACH/observers describe **circular arched gateways** on compound
walls **[S]** — is the same path with `R = S/2`:

```svg
<path d="M 0 0 A 50 50 0 0 1 100 0" fill="none"/>
```

**Use segmental for content (windows/cards), semicircular for thresholds (gates/CTAs).**
That distinction is real in the architecture and it gives you a free semantic rule.

### 1.2.3 Louvered shutter — texture with a correct physical rule

Louvers are defined by pitch `p` (vertical spacing), blade section width `w`, and tilt `α`
from horizontal. A louver is **sight-tight** (no straight horizontal line of sight passes)
when:

```
w · sin α ≥ p
```

**[D]** Therefore:

| Tilt `α` | Minimum blade width |
|---|---|
| 30° | `2.000 × p` |
| 35° | `1.743 × p` |
| 40° | `1.556 × p` |
| **45°** | **`1.414 × p`** |

Traditional shutters run roughly `α = 35–45°` **[I]**. At 45° the blade is `√2 × p` —
another clean constant.

As a CSS texture (a shutter reads as a hairline stripe field, not as drawn blades):

```css
/* louver field: 1px dark line, 6px light — pitch 7px */
.louver {
  background-image: repeating-linear-gradient(
    180deg,
    color-mix(in srgb, var(--ink) 18%, transparent) 0 1px,
    transparent 1px 7px
  );
}
```

For a shutter *panel*, inset the louver field inside a 3-part stile-and-rail frame:
outer frame `0.06 × panel width`, a mid-rail at `0.55` of the height **[I]**. Two louver
fields, unequal — the lower one taller. Never split a shutter 50/50.

### 1.2.4 Compound wall + gateway

The street elevation is: **high blank wall, punctuated by a tall arched gateway.** **[S]**
Wall height ≈ `2.0–2.4 × gate width` **[I]**. The gate is the only opening; the wall
carries only a cap moulding and, sometimes, a shallow pilaster at each side of the gate.

This is a *whole navigation metaphor*: long quiet runs, rare emphatic openings.

## 1.3 Palette

**All hexes are my calibration of sourced colour names. No official code exists. [X]**

| Name (as used in sources) | Hex | Notes |
|---|---|---|
| Sunburnt yellow / Pondy mustard | `#e0a32e` | the signature field colour **[S]** for the name |
| Pale limewash yellow | `#efd49a` | the faded/weathered state of the same wash |
| Peach | `#f2c3a7` | second most common field colour **[S]** |
| Lime white (trim) | `#f7f4ee` | pilasters, bands, cornices, parapet |
| Shutter green | `#2e4a3c` | **near-identical to your existing `bottle` `#1d3d33`** |
| Shutter grey-green | `#6e7a65` | the weathered alternative |
| Mangalore tile terracotta | `#b5583a` | roofs, mostly Tamil quarter |

**[X] Shutter colour conflict:** sources variously describe shutters as grey, grey-green,
deep green, and blue. All four occur in the quarter. Do not treat any single one as
canonical — but **deep green is the one that matches your palette**, so use it.

## 1.4 How it serves the UI

- **Card frame** = panel: hairline band inset `0.045` of card width, segmental-arched top
  edge only on hero/feature cards.
- **Section divider** = the one heavy cornice: a `2px` ink rule with a `1px` brass rule
  `6px` below it. Rare. Two per page maximum.
- **Background system** = the pilaster rhythm as a very low-contrast vertical hairline
  field at the page margins (`opacity ≈ 0.06`).
- **Layout grid** = bay pitch. Pick one bay width and let every card, gutter and inset be
  a rational fraction of it.
- **Texture** = louver stripe on inactive/empty states and on the back of overlays.

---

# 2. Puducherry Tamil Quarter — *Ville Noire*

## 2.1 What it actually looks like

The native Tamil town grew around a nucleus of temples in the north, streets laid on an
**east–west axis**, with back-to-back row houses opening onto them. **[S]** Like the
French quarter it is continuous wall-to-wall — but the resemblance stops there. **[S]**

The exterior is defined by two elements. The **thalvaram** is a street verandah with a
lean-to roof carried on wooden posts — a social extension of the house that shelters
passers-by. **[S]** The **thinnai** is a semi-public verandah with **masonry benches for
visitors and pilgrims**, marking "the sensitive transition space after which the house is
entered through a finely carved wooden door." **[S]** Inside, the **mutram** — a
colonnaded courtyard — is the central family space around which everything else is
functionally arranged; larger houses have several courtyards. **[S]**

INTACH calls these **"talking-streets"**, and gives the single best description of the
system: the street is homogeneous "because of connecting elements like lean-to-roofs,
cornices (horizontals), and pilasters and engaged columns (verticals) with ornamental
parapets, which define the skyline. **All houses are similar, but no two houses are
exactly the same.**" **[S]**

That last sentence is the design brief for a card system.

The two quarters interpenetrate. In many two-storey Tamil houses "the ground floor is
usually Tamil type with thinnai, thalvaram, pillared courtyard and carved wooden doors,
while the first floor displays French influence through fluted pilasters, columns with
capitals, arched windows, plaster decorations and end-ornament elements." **[S]** This
hybrid is what INTACH calls **Franco-Tamil**, and it is the town's actual signature.

## 2.2 Concrete geometry

### 2.2.1 The thinnai section — a real, usable profile

```
                        ┌──── lean-to roof (thalvaram), pitch 22–30° [I]
                   ╱────┘
              ╱────                      <- Mangalore tile needs ≥22.5° [I]
         ╱────
   ┌─────┴─────┐  wooden post
   │           │
   │  ┌────────┴────────┐  ← door (carved)
───┤  │   THINNAI       │
   │  │   platform      │
   └──┴─────────────────┴──── street
      |<--- d --->|
```

| Element | Value | Marker |
|---|---|---|
| Thinnai seat height above street | 450–600 mm | **[I]** ergonomic bench range |
| Thinnai platform depth `d` | 900–1200 mm | **[I]** |
| Post spacing (thalvaram bay) | 1.8–2.4 m | **[I]** |
| Lean-to pitch | 22–30° | **[I]** Mangalore pattern tile minimum ≈22.5° |

The thinnai is a **raised plinth in front of the entrance**. That translates directly to a
card with a raised, slightly inset "shelf" band above its primary action.

### 2.2.2 Carved wooden column — the 4 → 8 → 16 → circle rule

**This is the single most transferable geometric idea in the Tamil quarter.**

Traditional South Indian wooden and stone columns progress upward through a fixed
sequence of cross-sections **[I]** (classical terminology: *chaturasra* → *ashtasra* →
*shodasasra* → *vritta*):

```
   ○   circular       upper shaft
  ⬡    16-sided
  ⬢    octagonal
  ▢    square         base block
```

Each step **cuts the corners of the previous**, doubling the face count: **4 → 8 → 16 →
∞**. To go from an `n`-gon to a `2n`-gon by corner-cutting, chamfer each corner by:

```
c = s / (1 + 2·cos(π/n) ... )   -- or, simply and correctly for a regular polygon
    of circumradius R: the 2n-gon inscribed in the same R has side 2R·sin(π/2n)
```

**[D]** Practical version for UI, which is all you need:

| Step | Corner treatment | Suggested token |
|---|---|---|
| 4 (square) | `border-radius: 0` | `--corner-0` |
| 8 (octagon) | 45° chamfer of `0.293 × side` | `--corner-1` |
| 16 | chamfer of `0.098 × side` | `--corner-2` |
| ∞ (circle) | fully round | `--corner-3` |

`0.293 = 1 − cos(45°)` gives the true regular octagon from a square. **[D]**

Use it as a **hierarchy signal**, exactly as the column does: square at the base
(structural, containers), octagonal in the middle (cards), circular at the top (avatars,
status dots, the single ornamental element). Do not use arbitrary `border-radius`.

Octagon as a CSS clip-path (true regular octagon in a square box):

```css
.chamfer-8 {
  --c: 29.3%;
  clip-path: polygon(
    var(--c) 0, calc(100% - var(--c)) 0,
    100% var(--c), 100% calc(100% - var(--c)),
    calc(100% - var(--c)) 100%, var(--c) 100%,
    0 calc(100% - var(--c)), 0 var(--c)
  );
}
```

### 2.2.3 Courtyard (mutram) plan

Roughly square, colonnaded on one or both sides, with the roof sloping **inward** to it.
**[S]** In UI terms: a container whose padding is where the content actually lives, with
the "roof" (elevation/shadow) falling toward the centre rather than away from it — i.e.
an **inset** shadow, not a drop shadow.

```css
.mutram {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink) 8%, transparent),
              inset 0 2px 6px -4px color-mix(in srgb, var(--ink) 30%, transparent);
}
```

### 2.2.4 "All houses similar, no two identical" — as a generative rule

Implement literally:

- One fixed module (bay pitch, cornice height, parapet height) shared by every card. **Never vary.**
- One varying slot per card — the parapet ornament — drawn from a small finite set (4–6 variants).
- Variant selected deterministically by hashing the record ID, so a given startup always
  gets the same mark.

This gives a street that is homogeneous at a glance and individual on inspection. It is
also cheap: 6 SVG parapet motifs and a hash.

## 2.3 Palette

**Calibrated from photographic sources. [I]/[X] — no official codes.**

| Name | Hex | Notes |
|---|---|---|
| Mangalore tile terracotta | `#b5583a` | lean-to roofs |
| Aged teak / carved door | `#5a3a24` | doors, posts, brackets |
| Lime plaster (unpigmented) | `#efe9dc` | very close to your `alabaster` |
| Kumkum red band | `#a83b2a` | temple-adjacent trim, ornamental parapets |
| Turmeric ochre | `#d99b2b` | paired with the red in temple/threshold trim |
| Granite grey | `#6e6a63` | plinths, steps, thinnai facing |

Red-and-ochre paired banding is genuinely characteristic of temple-adjacent Tamil
building. Use it as a **rare** accent (a single 3px double-rule), never as a field.

## 2.4 How it serves the UI

- **Card frame** = thinnai: raised inset "shelf" strip at the card's leading edge, carrying
  the metadata; the carved door position becomes the primary action.
- **Section divider** = the lean-to: an asymmetric rule — thick at one end, hairline at the
  other, or a rule with a small triangular tick at 22–30°.
- **Background system** = the continuous street: cards butted edge-to-edge with a shared
  1px divider rather than floating with gutters. This is the biggest structural idea here
  and it is unusual enough to read as considered.
- **Layout grid** = courtyard: content wells with inset shadow, not raised cards.
- **Corner tokens** = the 4→8→16→circle ladder.

---

# 3. Auroville — Matrimandir, Roger Anger

## 3.1 What it actually looks like

A flattened golden sphere sitting in a sunken crater at the centre of a 2.5 km-wide
circular city plan, surrounded by twelve stone-clad petals and a red sandstone
amphitheatre. The dome is clad in **gold-leafed stainless steel discs**; the inner skin is
a white fibreglass fabric over triangular frames, pierced by portholes filtered to a
translucent golden-pink. **[S]** Inside, a pure white 12-sided chamber, lit by a single
vertical sunbeam that a roof-mounted heliostat tracks and focuses through two lenses onto
a 70 cm optically perfect glass globe. **[S]**

It is not decorative. Every element is a number: 12, 4, 216, 1415. The aesthetic is
**white marble, gold, and geometry** — which is very close to `alabaster + brass`.

### Sourced dimensions

| Element | Value | Marker |
|---|---|---|
| Sphere | **36.0 m diameter × 29.5 m high**, flattened | **[S]** |
| Sphere height (alternate) | 23.5 m | **[X]** Wikipedia gives 23.5 m; matrimandir.org / Auroville give 29.5 m. Likely above-ground vs. total, but **unresolved** — do not quote a single figure without qualification. |
| Golden discs, total | **1,415** | **[S]** |
| — small, convex | 954, avg **1.5 m** dia | **[S]** |
| — large, concave | 461, avg **2.3 m** dia | **[S]** |
| Gold leaf | 85 × 85 mm, 28 g per 1,000 leaves, ~750,000 leaves, ~18 kg total | **[S]** |
| Inner skin | 756 triangular frames | **[S]** |
| Portholes | **668** or **800** | **[X]** matrimandir.org says 668; other Auroville pages say 800 |
| Inner Chamber | radius **12 m**, **12-sided**, walls **8.65 m**, apex **15.2 m** | **[S]** |
| Ceiling | 12 facets, nominally **30°** rising to centre | **[S]** |
| Chamber columns | **12**, **60 cm** dia, white lacquer, at **half-radius (6 m)** toward each corner, **non-structural** | **[S]** |
| Crystal globe | **70 cm** dia, Bohr Kron 7 glass | **[S]** |
| — weight | 1,100 kg (rough casting) / 400 kg (finished) | **[X]** both figures published; the pair is consistent if one is pre-grinding |
| Sun-spot on globe | **180 mm** | **[S]** |
| Lens 1 / Lens 2 | 45 cm dia, f = 30 m / 25 cm dia, f = 5 m | **[S]** |
| Large petals | 12, within a **49 m radius** circle, **6.50 m** high | **[S]** |
| Small petals | 12, within a **76 m radius** circle | **[S]** |
| Lotus pond | **216** petal-shaped marble slabs; central crystal **17 cm** | **[S]** |
| Amphitheatre | inner dia **75 m**, outer dia **98 m**, depth **2.2 m**; 4,400 m² / 7,500 m² | **[S]** |
| Four entrance pillars | Mahakali N = **red square**; Maheshwari S = **orange hexagon**; Mahalakshmi E = **pink circle**; Mahasaraswati W = **light blue triangle** | **[S]** |

### Galaxy plan (Auroville city)

| Element | Value | Marker |
|---|---|---|
| City area | circle of **2.5 km diameter** (radius **1.25 km**), 1,227 acres / ~500 ha | **[S]** |
| Green Belt | further **1.25 km** wide band → overall **5 km** diameter | **[S]** |
| Target population | 50,000 | **[S]** |
| The Crown | circular road around the Matrimandir Peace Area | **[S]** |
| Radial roads | **twelve**, radiating outward from the Crown | **[S]** |
| Zones | Industrial N, Cultural NE, Residential S/SW, International W | **[S]** |
| "Lines of Force" | spiral arms unwinding from the centre; high-rise corridors on selected radials | **[S]** |
| Spiral pitch angle / Crown radius | **not published** | **[X]** — do **not** invent a logarithmic-spiral constant. Roger Anger himself: "the plan is not finished… everything is flexible, nothing is fixed" beyond the Lines of Force. **[S]** |

## 3.2 Concrete geometry

### 3.2.1 The dodecagon — the master figure

Twelve appears everywhere: 12-sided chamber, 12 columns, 12 ceiling facets, 12 large
petals, 12 small petals, 12 gardens, 12 radial roads. **Adopt 12-fold division (30°
increments) as the project's rotational constant.** **[S]** for the count, **[D]** for
the maths:

For a regular 12-gon of circumradius `R`:

```
vertex k at angle 30k degrees, k = 0..11
side length      s = 2R·sin(15°)  = 0.517638 R
apothem          a =   R·cos(15°) = 0.965926 R
interior angle   = 150°
area             = 3R²            (exactly)
```

The apothem is **96.6% of the circumradius** — which is why a 12-gon reads as a circle at
UI scale. Use it as a *subliminal* container shape: at 40px it looks round, at 400px it
declares itself.

```svg
<!-- regular 12-gon, R=100, centred at 0,0 -->
<polygon points="100,0 86.60,50 50,86.60 0,100 -50,86.60 -86.60,50
                 -100,0 -86.60,-50 -50,-86.60 0,-100 50,-86.60 86.60,-50"/>
```

**Consistency check on the chamber [D]:** a 30° ceiling over a 12 m half-span would rise
`12·tan30° = 6.93 m`, giving an apex at `8.65 + 6.93 = 15.58 m`. The published apex is
**15.2 m**, which implies **28.6°**. So "30°" is nominal, not measured. Use 30° — it is
the intent — but know the discrepancy exists.

### 3.2.2 Golden-disc field — a two-size circle texture

Two disc sizes, two counts:

```
diameter ratio  2.3 / 1.5 = 1.533
count ratio     954 / 461 = 2.07  ≈  2 : 1
```

**[D]** So: **twice as many small discs as large, small : large diameter ≈ 1 : 1.53.**

Sanity check **[D]**: total disc area `954·π·0.75² + 461·π·1.15² = 3,601 m²` against a
36 m sphere's `4π·18² = 4,072 m²` → **88% coverage**. The figures are mutually consistent,
which supports the sourced counts.

Implementation: a background of brass-tinted circles at two radii, ratio 1:1.53, in a 2:1
population, jittered onto a 12-fold radial lattice. Small discs convex (highlight top-left),
large discs concave (highlight bottom-right) — that inversion is what makes the real dome
shimmer. **[S]**

```css
/* extremely low-contrast brass disc field for a hero ground */
.disc-field {
  background-image:
    radial-gradient(circle 7px at 25% 25%,  color-mix(in srgb, var(--brass) 14%, transparent) 98%, transparent),
    radial-gradient(circle 11px at 70% 62%, color-mix(in srgb, var(--brass) 10%, transparent) 98%, transparent);
  background-size: 46px 46px, 92px 92px; /* 2:1 population */
}
```

### 3.2.3 The amphitheatre — offset concentric circles

This is the most beautiful reproducible rule in the whole document, and it is directly
sourced: the steps **"form a family of circles whose centres are evenly spaced along a
line which includes the Urn."** **[S]**

Construction:

```
for i = 0 .. n:
    r_i  = R_inner + i · ΔR          ΔR = (R_outer − R_inner) / n
    c_i  = (i · Δc, 0)               Δc  = constant, with Δc < ΔR
```

With the real numbers **[S]/[D]**: `R_inner = 37.5 m`, `R_outer = 49 m`, radial band
`11.5 m`, depth `2.2 m` → mean rake `atan(2.2 / 11.5) = 10.83°`, about 1 : 5.2.

Because `Δc < ΔR`, the circles remain nested but **eccentric**: the tier band is narrow on
the urn side and wide opposite. That single asymmetry is what stops a concentric-circle
graphic from looking like a target.

```svg
<!-- 8 tiers, R 37.5 -> 49, centres marching +0.9 per step toward the urn at left -->
<g fill="none" stroke="currentColor" stroke-width="0.4">
  <circle cx="0.0" cy="0" r="37.5"/>
  <circle cx="0.9" cy="0" r="39.14"/>
  <circle cx="1.8" cy="0" r="40.79"/>
  <circle cx="2.7" cy="0" r="42.43"/>
  <circle cx="3.6" cy="0" r="44.07"/>
  <circle cx="4.5" cy="0" r="45.71"/>
  <circle cx="5.4" cy="0" r="47.36"/>
  <circle cx="6.3" cy="0" r="49.00"/>
</g>
```

### 3.2.4 Four cardinal glyphs — a ready-made icon system

Sourced and unambiguous **[S]**:

| Direction | Aspect | Shape | Colour (source name) |
|---|---|---|---|
| North | Mahakali | **square** | red |
| South | Maheshwari | **hexagon** | orange |
| East | Mahalakshmi | **circle** | pink |
| West | Mahasaraswati | **triangle** | light blue |

Four primitives — square, hexagon, circle, triangle — already differentiated and already
carrying meaning. This is a legitimate, non-decorative basis for a category/status marker
set. Draw them monochrome in `ink` or `brass`; the source colours are too saturated for
this UI (see §3.3).

### 3.2.5 Galaxy plan geometry you can safely use

Only two ratios are solidly published, and they are both clean **[S]**:

```
city radius : green-belt outer radius  =  1.25 km : 2.50 km  =  1 : 2
radial roads from the Crown            =  12       (30° apart)
```

Everything beyond that — spiral pitch, Crown radius, zone angular extents — is **[X]
unpublished**. If you draw a spiral, label it a reconstruction. A defensible neutral
choice is a logarithmic spiral `r = a·e^(bθ)` with `b` set so the arm sweeps from
`0.25 R_city` to `R_city` over 180°, i.e. `b = ln(4)/π ≈ 0.4413` — but this is **my
construction, not Anger's**.

## 3.3 Palette

| Name | Hex | Marker |
|---|---|---|
| Gold leaf (disc, direct light) | `#d4af37` | **[I]** rendering of "gold-leafed" **[S]** |
| Gold leaf (shadow / raking) | `#a8862c` | **[I]** — very near your `brass #9a7b45` |
| Lasa white marble | `#f2f0ec` | **[I]** — very near your `alabaster #f4f1ea` |
| Inner-skin golden-pink | `#e9a98e` | **[I]** rendering of "translucent orange-pink" **[S]** |
| Red Agra sandstone (amphitheatre) | `#a6503c` | **[I]** rendering of "Agra stones from Rajasthan" **[S]** |
| Mahakali red | `#c1272d` | **[I]** rendering of a **[S]** colour name |
| Maheshwari orange | `#e07b26` | **[I]** |
| Mahalakshmi pink | `#e8a0b4` | **[I]** |
| Mahasaraswati light blue | `#a8cbe0` | **[I]** |

**Recommendation:** take **gold + white marble** (they are effectively `brass` +
`alabaster`) and take the **geometry**. Leave the golden-pink and the four saturated
aspect colours alone — they will destroy the editorial restraint.

## 3.4 How it serves the UI

- **Rotational constant**: 12-fold / 30° everywhere a radial figure is needed (loaders,
  progress rings, radar/spider charts, sunbursts).
- **Background system**: the offset-concentric amphitheatre family, at `opacity 0.05` in
  brass, anchored off-canvas so only an arc segment shows.
- **Texture**: the two-size golden disc field for hero and empty states.
- **Icon primitives**: square / hexagon / circle / triangle, cardinal-coded.
- **Container shape**: 12-gon that only reveals itself above ~200px.
- **Ratio**: 1:2 (city : green belt) as a legitimate spacing ratio for outer margins.

---

# 4. Madras Art Movement & Cholamandal — *the most transferable tradition here*

## 4.1 What it actually looks like

K.C.S. Paniker was principal of the Government College of Arts and Crafts, Madras, and
founded **Cholamandal Artists' Village in 1966** as a self-sufficient artists' cooperative
on the outskirts of the city — still one of India's largest artist communes. **[S]**
Between **1963 and 1975** he produced **Words and Symbols**, the series that defines the
movement. **[S]**

The construction is remarkably specific and remarkably close to editorial layout: **"In
many of his 'Words & Symbols' paintings, Paniker employed thin vertical and horizontal
lines to cordon off space on the surface of the canvas, filling it with inscrutable
notes."** **[S]** The compartments hold **illegible script** (Malayalam-like calligraphic
marks, plus text in English and Sanskrit "that cannot be read beyond a word or two"),
**mathematical symbols and equations**, **diagrams hinting at astrology and birth charts**,
**tantric yantras**, **kolam patterns**, and sparse linear drawings of rivers, trees, birds
and animals. **[S]** A curator's formulation of the movement's core: "the line meets text
which could be both legible or illegible." **[S]**

Palette moved lighter over the series — **"pinkish pigments and foggy atmospheric
qualities"** replacing his earlier darker grounds. **[S]**

Around him: **J. Sultan Ali** built compositions from folk and tribal deities, tribal
jewellery motifs, text elements and arid landscape features, held in heavy outline. **[S]**
**K.M. Adimoolam** worked abstract, known for colour observations of nature — and,
separately, for large bodies of pure ink line drawing. **[S]** **S. Dhanapal** (sculptor,
co-founder of Cholamandal) and **S. Nandagopal** developed **angular, flat, elongated,
frontal** forms — deliberately anti-volumetric — drawing on South Indian temple carving.
**[S]** **P.V. Janakiram** made sheet-metal sculpture in **repoussé**. **[S]** The village
also produced batik, engraving, jewellery, woodwork, pottery, terracotta and weaving. **[S]**

**The metal-relief strand matters for you specifically: brass and copper repoussé, worked
flat and linear, is exactly `#9a7b45` used as line rather than as fill.**

## 4.2 Concrete geometry

### 4.2.1 The compartmented register field — *the primary system*

This is Paniker's construction rule and it is a layout engine.

```
Rules:
  R1. Partition a rectangular field with thin straight rules, orthogonal only.
  R2. Rules are HAIRLINE relative to the field:  w ≈ field_width / 800  (min 1 device px)
  R3. Cells are UNEQUAL. No repeated module. Aspect ratios ~0.4 to ~3.0.
  R4. Some rules run edge to edge; some TERMINATE against another rule; a few
      stop short of any rule (a free end). Free ends are what stop it looking
      like a table. Target ~15–20% free ends.
  R5. Cell fill is one of exactly four kinds:
        (a) empty ground
        (b) a run of script-like marks (§4.2.2)
        (c) a diagram (§4.2.3 or §4.2.4)
        (d) a single sparse line drawing
      Never two kinds in one cell.
  R6. Density gradient across the field: one quadrant near-empty. The empty
      quadrant is what makes it read as composed rather than filled.
```

This maps onto CSS Grid with `grid-template-areas` and hairline `outline`s, or onto a
seeded recursive binary subdivision (split each cell at a random ratio in `[0.32, 0.68]`,
alternating axis, stop at depth 3–4).

### 4.2.2 Script-like marks — asemic text as texture

The marks are **illegible**. That is a feature: it removes any need to typeset real Tamil
in decorative positions, and it removes the risk of mistranslation.

Construction rules for asemic Tamil-flavoured marks **[I]**, informed by the real script
characteristics in §5:

```
- Baseline-aligned run, constant "Pa-height" h.
- Each mark = 1–3 strokes, built ONLY from:
      • circular arcs of radius h/2 and h/4
      • short verticals of length h
      • a leftward horizontal "beak" tick of length h/4 at the top of some marks
- NO long straight diagonals. Tamil has essentially none (see §5.2).
- Stroke weight: h/9 to h/7, monoline.
- Advance width: 0.55h to 0.95h, varied.
- Word gaps: 1.2h, at irregular intervals of 3–8 marks.
- Line spacing: 1.9h  (Tamil needs more leading than Latin)
```

Render at `opacity 0.10–0.16` in `ink` as a texture; at full opacity only as a deliberate
graphic element, never adjacent to real copy where a reader might try to read it.

### 4.2.3 The birth-chart grid (rasi chart) — 4×4 minus centre

Paniker's canvases contain **"diagrams that hint at astrology and birth charts."** **[S]**
The South Indian *rasi* chart is a fixed, exact figure and it is trivially drawable:

**A 4×4 grid with the central 2×2 merged into a single cell → 12 perimeter cells.**

```
┌───┬───┬───┬───┐
│ 1 │ 2 │ 3 │ 4 │
├───┼───┴───┼───┤
│ 12│       │ 5 │
├───┤       ├───┤
│ 11│       │ 6 │
├───┼───┬───┼───┤
│ 10│ 9 │ 8 │ 7 │
└───┴───┴───┴───┘
```

Twelve cells again — it rhymes with the Matrimandir's 12-fold division, which is a real
gift for coherence. Use it for: a dashboard tile arrangement, a 12-month grid, a
category index, or a decorative mark at `opacity 0.08`.

```svg
<!-- 4x4 outer grid, centre 2x2 merged. side = 120 -->
<g stroke="currentColor" fill="none" stroke-width="1">
  <rect x="0" y="0" width="120" height="120"/>
  <path d="M30 0 V30 M60 0 V30 M90 0 V30
           M30 90 V120 M60 90 V120 M90 90 V120
           M0 30 H30 M0 60 H30 M0 90 H30
           M90 30 H120 M90 60 H120 M90 90 H120
           M30 30 H90 V90 H30 Z"/>
</g>
```

### 4.2.4 Kolam — pulli lattice, single closed curve

Paniker explicitly drew on **kolam** patterns. **[S]** The construction is genuinely
mathematical **[S]**:

- Dots (*pulli*) laid on an **equidistant lattice**, spacing `d`.
- The drawing is a **continuous closed curve** that partitions the plane into as many
  bounded regions as there are dots, **each region containing exactly one dot**. **[S]**
- Single-stroke kolams correspond to **Eulerian circuits** on the lattice graph. **[S]**
- Symmetry is automatic: mirror about the vertical axis, horizontal axis, or both, and the
  lattice guarantees alignment. **[S]**

Classic dot layouts: square `n×n`, or the diamond ramp **1-3-5-7-5-3-1** (rows of dots
increasing then decreasing by 2). **[I]**

For *sikku/kambi* (loop) kolam, the curve runs at **45° to the lattice** and turns using
**arcs of radius `d/2`** around individual dots, so each dot sits inside a loop. **[I]** —
the exact radius is a stylistic choice; `d/2` reproduces the common look.

```svg
<!-- one kolam loop cell: dot at centre, curve of four d/2 arcs. d = 40 -->
<circle cx="20" cy="20" r="1.6"/>
<path d="M20 0 A20 20 0 0 1 40 20 A20 20 0 0 1 20 40
         A20 20 0 0 1 0 20 A20 20 0 0 1 20 0 Z"
      fill="none" stroke="currentColor" stroke-width="1.5"/>
```

**Use kolam sparingly.** It is the most recognisable Tamil visual motif and therefore the
easiest to make look like a tourist brochure. One instance per surface, low contrast.

### 4.2.5 Yantra — nested squares and gates

Tantric diagrams appear throughout the series. **[S]** The reliably reproducible part is
the **bhupura** (outer frame): concentric squares with a **T-shaped gate** at the midpoint
of each side. **[I]** Nested circles, and a ring of lotus petals (typically 8 or 16 —
which rhymes with the column progression in §2.2.2), sit inside it.

**[X] Do not attempt an exact Sri Yantra.** Its nine interlocking triangles (4 upward, 5
downward) forming 43 small triangles have no simple closed-form construction, and the
"correct" version is genuinely disputed among scholars. A wrong one is worse than none.
Use the bhupura frame only.

## 4.3 Palette

**[I]/[X]** — derived from reproductions. Colour in art reproductions is unreliable;
treat these as a *family*, not as matches.

| Name | Hex | Notes |
|---|---|---|
| Ground, raw canvas / off-white | `#ede5d3` | close to `alabaster` |
| Raw sienna / ochre | `#b08245` | the dominant warm mid-tone |
| Burnt umber | `#6b4a2f` | |
| Iron black (line) | `#1a1714` | close to `ink` |
| Late-period fog pink | `#d8a79a` | the **[S]** "pinkish, foggy" shift |
| Cinnabar / kumkum accent | `#a83b2a` | sparse |
| Repoussé brass | `#9a7b45` | **exactly your existing `brass`** |
| Repoussé copper | `#8c5a3c` | Janakiram / Nandagopal metalwork |

This palette is the closest match to the existing system of anything in this document.
That is not a coincidence — both are earth-pigment, paper-ground, line-dominant systems.

## 4.4 How it serves the UI

- **Layout grid** — the compartmented register field is a genuine, unusual, *editorial*
  grid. This should be the backbone of the visual system.
- **Section dividers** — hairline rules with occasional free ends. A rule that stops 20%
  short of the margin is the single cheapest gesture that signals "designed".
- **Background system** — asemic mark runs at `opacity ≈ 0.10`, filling one or two cells of
  an otherwise empty register field.
- **Card frames** — cells, not boxes: shared hairlines, no gutters, no shadows.
- **Data display** — the rasi 12-cell grid; the kolam lattice as a chart background.
- **Mark-making as texture** — this is the term of art for exactly what Paniker does, and
  it is the right way to add richness without figuration.

---

# 5. Tamil Typography & Epigraphy

## 5.1 What it actually looks like

Tamil is a rounded, arc-based script with almost no long straight diagonals. The received
explanation — and the subject of D. Udaya Kumar's IIT-Bombay doctoral thesis
*Transformation of Tamil Letterforms from Palm Leaf Manuscripts to Early Letterpress
Printing* **[S]** — is that this roundness comes from the **stylus and palm leaf**: leaves
were incised with a pointed metal stylus, and long straight cuts along the grain split the
leaf, so scribes curved everything. **[I]** as a causal claim; **[S]** that the medium and
tools drove the evolution. Grooves were then rubbed with **lampblack** to make the letters
visible; there is no ink. **[S]**

On stone, the same script hardens. Chola scribes used **two scripts on the same wall**:
Tamil for the vernacular record and **Grantha** for Sanskrit passages, and the difference
is visible — **"deep, rounded incisions of the Tamil characters, contrasted with the more
angular Grantha letters."** **[S]** Inscriptions run as **continuous horizontal bands along
base mouldings and wall courses**, wrapping the building; lower registers are worn smooth
by centuries of touch while higher registers stay sharp. **[S]**

## 5.2 Concrete geometry — the Tamil spacing system

The best available formal analysis is Aadarsh Rajan's *Finding Patterns and Rhythms in
Tamil* (EkType / Typography Day 2016), documenting the design of **EkTamil**. Everything
in this subsection is **[S]** from that paper unless marked otherwise.

### 5.2.1 Vertical metrics

Tamil's body height is the **Pa-height** (the height of ப), not an x-height. The paper's
declared grid, fixed before drawing: **Pa-height, eye level, ascender, descender.**

**Eye level** = the height of the eye in the vowel ஏ. The bowl of த coincides with it.
**120 Tamil characters possess an "eye"**, and eye size *increases* as the eye falls
toward the baseline.

### 5.2.2 The **gate space** — the base unit of the whole script

> "the gate space (the space between the stems of the letter Ra)"

The gate is the counter between the two stems of the two-stemmed letter. **Its width is the
rhythm unit of Tamil.** The paper's rules, all of them directly implementable:

| Rule | Statement |
|---|---|
| **Inter-character spacing** | set **equal to the gate width**, across the whole font |
| **Ikaram spacing** | the space between the character and its ikaram = the space between two verticals |
| **Ukaram tails** | the **area** between base letter and tail is designed **equal to the gate area** (an *area* match, not a distance match) |
| **Ma counters** | open counter ≡ the Ra counter; closed counter ≡ the second counter of Rra |
| **Va** | the circular counter is condensed so it stops dominating; second counter ≡ curve-to-vertical space |
| **Ka window ≈ E eye** | the window of க occupies nearly the same *area* as the eye of ஏ |
| **Bowls ≈ lacrymal loops** | the bowl counters ≈ the loops on ண / ன in area |

### 5.2.3 The **beak** (*mukka*) — the asymmetry that matters

> "the horizontal protrusion to the **left** of characters such as Ra, Ta and Lla"

The beak collects extra space beyond the stem, so those glyphs cannot be tightly spaced.
EkTamil's solution: don't shorten the beak — **widen the whole font's spacing to the gate
width** so the beak's extra space is absorbed into a uniform rhythm.

**UI consequence:** Tamil needs **more letter-spacing and more leading than Latin at the
same size**, and Tamil needs to be **set larger** than Latin so the Latin does not appear
oversized beside it. **[S]** Practical starting values **[I]**:

```css
:lang(ta) {
  font-size: 1.08em;      /* Tamil up, so Latin doesn't dominate */
  line-height: 1.75;      /* vs ~1.5 for the Latin */
  letter-spacing: 0.005em;
  word-spacing: 0.06em;   /* word gap must clearly exceed the gate rhythm */
}
```

### 5.2.4 The four degrees of space — a spacing-token ladder

The paper's own taxonomy, which is an unusually good fit for a design-token scale:

| Degree | Name | Definition |
|---|---|---|
| **1st** | **Base spaces** | vertical–vertical, curve–vertical, curve–curve |
| **2nd** | **Gate spaces** | the intra-character rhythm unit |
| **3rd** | **Eye spaces** | spaces in characters with an eye on the baseline |
| **4th** | **Anomalous spaces** | the "wells and lakes" — coagulated white from ப, ட, Uukarams, Grantha letters |

Consider naming the spacing scale after this: `--space-base`, `--space-gate`,
`--space-eye`, `--space-well`. It is a genuine local system, not a decoration.

### 5.2.5 The signage painter's method — directly usable

> "Some signage artists also paint Tamil signage by first drawing **all the verticals in a
> word** and then connecting them in intricate ways to reveal letters. This, they feel, is
> a better practical judge of rhythm and space."

The painter, using a **left-canted brush**, achieves a more even grey than most newspaper
typefaces, compressing Va, Ma and La into a **regimented gate rhythm**. The paper also
notes: to control the space under the beak, painters start the stroke closer to the stem
and **turn the brush right below the beak**.

**This is the correct way to build a decorative Tamil-flavoured mark field: lay the
verticals first on a strict pitch, then connect them.** It guarantees even colour.

### 5.2.6 Palm leaf (*olai chuvadi*) layout

| Quantity | Value | Marker |
|---|---|---|
| Leaf width | ~**4 cm** average | **[S]** |
| Leaf length | ~**48 cm** average | **[S]** |
| **Aspect ratio** | **1 : 12** | **[D]** |
| Binding | hole(s) pierced, string threaded after scribing | **[S]** |
| Ink | none — incised, then lampblack rubbed in | **[S]** |
| Word spacing / punctuation | essentially absent (*scriptio continua*) | **[S]** |
| Lines per leaf | ~3–6 | **[I]** inferred from the 4 cm width; not surveyed |

**The 1:12 ratio is the deliverable here.** A `1:12` band is extreme, disciplined and
unmistakably derived — perfect for a page-top rule, a section header band, or a footer.
Note that 12 appears yet again (§3.2.1, §4.2.3).

### 5.2.7 Stone inscription (*kalvettu*) conventions

| Convention | Marker |
|---|---|
| Text runs as a **continuous horizontal band**, wrapping the building, on base mouldings and wall courses | **[S]** |
| **Registers** stack; different registers have different wear | **[S]** |
| **Two scripts on one surface**: rounded Tamil for vernacular record, angular Grantha for Sanskrit | **[S]** |
| Letters are **deeply incised**, not raised | **[S]** |
| Band height, letter height, ground clearance | **not published in any source I could reach** — **[X]** |

**UI translation:** a running metadata band that wraps a container edge-to-edge and
continues around a corner, at small size, with generous tracking. The *two-script* rule
gives you a legitimate typographic device: **rounded/humanist for the vernacular content,
a more angular/condensed face for formal or system content, on the same surface.**

## 5.3 Palette

| Name | Hex | Marker |
|---|---|---|
| Fresh palm leaf | `#c9a66b` | **[I]** |
| Aged palm leaf | `#b08e56` | **[I]** |
| Bleached / cleaned leaf | `#e6dcc4` | **[I]** — near `alabaster` |
| Lampblack in groove | `#1b1815` | **[I]** — near `ink` |
| Granite (sharp/upper register) | `#6e6a63` | **[I]** |
| Granite (worn/lower register) | `#8a857c` | **[I]** |

The two-value granite pair is useful in itself: **sharp = active, worn = disabled.**

## 5.4 How it serves the UI

- **Typographic treatment**: the gate-space spacing system; Tamil sized up 8% against
  Latin with 1.75 leading; the four-degree spacing tokens.
- **Section dividers**: the 1:12 palm-leaf band.
- **Card frames**: the inscription band — running metadata wrapped along a container's
  bottom edge in small, widely tracked caps.
- **Mark-making**: "verticals first, then connect" as the generator for asemic fields.
- **Two-script device**: rounded for content, angular for system — genuinely rooted.

---

# 6. Contemporary Tamil Nadu Public Art & Signage

## 6.1 What it actually looks like

**Chennai street signs.** Hand-painted, **black on yellow**, at eye level, painted directly
onto the wall of a house, a temple or a boundary wall at street corners and junctions.
**[S]** Layout: **Tamil above, Latin below**; the ward is in **smaller red lettering above
or below** the name; a **red arrow** may indicate which road is meant; **the street number
is set larger so that it serves both scripts and doesn't have to be written twice**. **[S]**
The **same brush** is used for both scripts, so Tamil and Latin come out at **near-equal
weight** — a subtlety most digital bilingual signage fails. **[S]** Painters work on site,
accounting for available light and surrounding signage, and will paint **around or over**
an obstruction rather than move the sign. **[S]**

**Sign painting generally.** Indian sign painting favours **three-dimensional letterforms**
built by shading and perspective — technically **bevelled prismatic lettering**, with fine
lines and triangles drawn inside sans-serif letters, then lit with contrasting highlights
and shadows. **[S]** The *satrangi* (seven-colour) style pushes up to seven colours inside
a single letter. **[S]** Tin boards gave way to acrylic sheets in the 1980s. **[S]**

**Cinema banners.** Rooted in 1948 (*Chandralekha*), and a full trade by 1950 (K. Mohan /
Mohan Arts). **[S]** Method: **'gada' cloth bought in pieces and stitched into one large
canvas; wooden pieces nailed into a frame; a "water coat" of `vajram` gum mixed with chalk
powder; then an oil coat.** **[S]** Images were transferred by **magic lantern** — a
rudimentary projector casting a photographic slide onto the canvas. **[S]** Vinyl printing
displaced the hand-painted banner and cut-out. **[S]**

## 6.2 Concrete geometry

### 6.2.1 The bilingual sign block — a real, reusable layout rule

```
┌──────────────────────────────────┐
│ ward name (small, red)           │   ← 0.45× main
│ ┌──┐  தமிழ்ப் பெயர்              │   ← Tamil, primary
│ │15│  ROMAN NAME                 │   ← Latin, same stroke weight
│ └──┘                             │   ← number spans both lines
└──────────────────────────────────┘
   black lettering on yellow field
```

Rules **[S]** except where marked:

1. Tamil **above** Latin. Always.
2. **Equal stroke weight** between scripts (same brush). In CSS: pair a Tamil and a Latin
   face whose stem weights match at the same optical size — do not just use the same
   numeric `font-weight`.
3. The **number is shared**: set it once, larger, vertically centred across both script
   lines, so it is not repeated. This is an elegant space economy and worth stealing
   outright for any bilingual list row.
4. Ward/secondary info: **smaller and red**, above or below.
5. Optional **red directional arrow**.
6. Field is **yellow**, lettering **black**, with no border **[I]** — the wall is the border.

### 6.2.2 Bevelled prismatic lettering

Construction **[I]**, from the **[S]** description:

```
- Start with a heavy sans/grotesque letterform.
- Find the medial axis of each stroke.
- Draw facet lines from every corner of the outline to the medial axis
  -> each stroke becomes a chain of triangles and quadrilaterals.
- Light source fixed, conventionally upper-left.
- Facets facing the light: base colour lightened ~35%.
  Facets facing away:      base colour darkened  ~40%.
- Optional hard drop shadow, offset (0.10em, 0.10em), no blur.
```

At UI scale this is far too loud for the whole system, but it is legitimate for **one**
element — a logotype, a milestone badge, an award marker.

### 6.2.3 Cinema banner construction as a *layout* metaphor

The banner is **stitched from pieces of cloth into one large surface**, then **primed
uniformly** (vajram gum + chalk, then oil) so the seams vanish under a single ground.
**[S]**

That is a precise description of what a good dashboard should do: **compose from
independently authored panels, then unify with a single ground treatment so the seams do
not read.** It also licenses a deliberate design move — a faint visible seam line at panel
joins, at very low contrast, as an honest trace of assembly.

The **magic lantern / squaring-up** method (project or grid a small study onto a large
surface) is the responsive-design metaphor: one composition, `n` scales, ratios preserved.
**[S]** for the method; the analogy is mine.

## 6.3 Palette

| Name | Hex | Marker |
|---|---|---|
| Municipal sign yellow | `#efc031` | **[I]** rendering of "black on yellow" **[S]** |
| Sign black | `#131313` | **[S]** the colour is sourced; the hex is mine |
| Ward red | `#c8102e` | **[I]** rendering of "smaller red lettering" **[S]** |
| Banner flesh/ground primer (chalk) | `#e8e2d4` | **[I]** |
| Banner cinnabar | `#c1341f` | **[I]** |
| Banner cobalt | `#1f4e8c` | **[I]** |

**Warning.** This is the *loudest* palette in the document and it is the one to keep out of
the product surface. Sign yellow at any real area will demolish an alabaster/ink/bottle
green system. Use it only as a **1–3% accent**: a single caution chip, a "hand-painted"
easter egg, or a marketing page — never as a UI colour.

## 6.4 How it serves the UI

- **Typographic treatment**: the bilingual block rule (Tamil above, equal weight, shared
  number) is the highest-value item in this section and should go straight into the
  component library for any bilingual list row.
- **Section dividers**: the faint seam line from banner construction.
- **Card frames**: none — signage has no frames; the wall is the frame. That is itself a
  useful instruction: some content should sit directly on the ground with no container.
- **Mark-making**: bevelled prismatic treatment on exactly one element.
- **Layout grid**: squaring-up as the responsive scaling discipline.

---

# TOP 5 FOR IMPLEMENTATION

Ranked by how well each survives translation into a restrained, premium, editorial web UI
— and by how well it sits on `alabaster / ink / bottle-green / brass`.

---

## 1. Paniker's compartmented register field (§4.2.1) — *the backbone*

**Why it wins.** It is already a layout grid. Thin orthogonal rules partitioning a field
into unequal cells, some rules terminating in free ends, one quadrant left empty — this is
exactly what a sophisticated editorial system does, and it arrives with genuine provenance
instead of being imported from Swiss modernism. It is abstract, so it carries zero risk of
the "cultural pastiche" failure mode. It scales from a full-page grid down to a 40px
ornament. And the asemic script fills (§4.2.2) give you infinite non-repeating texture
without ever rendering a decorative letterform that a Tamil reader could find wrong.

**Palette fit — the best in the document.** Paniker's system *is* an ink-line-on-warm-paper
system. `ink #14120f` ≈ his iron black. `alabaster #f4f1ea` ≈ his off-white ground. The
raw-sienna family (`#b08245`) sits a shade warmer than `brass #9a7b45` and can be used as
a second warm tone without introducing a new hue. Nothing has to change.

**Ship first:** hairline register grid + free-ended dividers + asemic texture at
`opacity 0.10`.

---

## 2. French Quarter facade panel system (§1.2) — *the frame language*

**Why it's second.** It gives you three separate, well-defined mechanisms in one tradition:
the **pilaster/cornice panel division** (card and section framing), the **segmental arch**
(a mathematically exact, elegant curve at `R = 5S/6` with a 3-4-5 half-angle — far more
refined than a `border-radius`), and the **louver stripe** (a texture with a correct
physical rule behind it). The compound-wall-and-gateway rhythm — long quiet runs, rare
emphatic openings — is a defensible information-architecture principle, not just an
ornament. And the "one heavy horizontal only" rule is exactly the kind of constraint that
makes a system look expensive.

**Palette fit — excellent, and slightly uncanny.** The shutter green I calibrated
(`#2e4a3c`) is essentially your `bottle #1d3d33`. The lime-white trim is your `alabaster`.
The one thing to *resist* is the sunburnt yellow field — it is the quarter's signature but
it will fight the brass. **Keep the yellow out; keep the green shutters, the white trim
and the geometry.**

**Ship first:** segmental-arch top on hero cards; louver texture for empty/inactive states.

---

## 3. Tamil column 4→8→16→circle + thinnai (§2.2.2, §2.2.1) — *the corner and shelf language*

**Why it's third.** The corner progression is the rarest idea here: a **principled corner
system** where roundness signals hierarchy rather than being chosen by feel. Square for
structure, octagon for cards, circle for the single ornamental top note. It comes with an
exact number (`0.293` chamfer for a true octagon from a square) and it maps to four design
tokens. The **thinnai** adds a second idea — the raised threshold shelf — which is a real
card affordance nobody else is using. And the "all houses similar, no two identical"
generative rule (§2.2.4) solves the card-monotony problem with 6 SVG variants and a hash.

**Palette fit — good, with a caveat.** Aged teak `#5a3a24` and granite `#6e6a63` are
comfortable neutrals alongside `ink`. The kumkum-red / turmeric-ochre pairing is authentic
but hot; restrict it to a single 3px double-rule on a threshold element, if at all.

**Ship first:** the four corner tokens; the thinnai shelf on the primary card.

---

## 4. Matrimandir 12-fold geometry + offset-circle amphitheatre (§3.2.1, §3.2.3) — *the rotational constant and the background*

**Why it's fourth.** It supplies the one thing the other traditions don't: a **rotational
system**. Twelve-fold division at 30° gives you a coherent basis for every radial figure in
the product, and it rhymes with two independent sources — the 12-cell rasi chart (§4.2.3)
and the 1:12 palm-leaf ratio (§5.2.6). The dodecagon whose apothem is 96.6% of its
circumradius is a lovely piece of restraint: round at 40px, deliberate at 400px. The
amphitheatre's **offset concentric circles** — a sourced construction rule, not an
invention — is the best background system in the document, because the eccentricity is
precisely what stops concentric circles reading as a target. The four cardinal glyphs
(square/hexagon/circle/triangle) are a ready-made icon basis.

**Palette fit — very good if you edit hard.** Gold-leaf-in-shadow `#a8862c` and Lasa marble
`#f2f0ec` are effectively `brass` and `alabaster`. **Discard** the golden-pink inner skin
and all four saturated aspect colours — they belong to a building, not to this UI.

**Ship first:** 30° as the rotational constant; the offset-circle arc at `opacity 0.05` in
brass, anchored off-canvas.

---

## 5. Tamil spacing system + bilingual sign block (§5.2, §6.2.1) — *the typographic layer*

**Why it's fifth but non-optional.** Ranked last only because it is invisible when done
right. The **gate space** as the base spacing unit, the four-degree space ladder as token
names, Tamil set 8% larger at 1.75 leading against the Latin, and the **beak's**
left-asymmetry are all documented, specific, and correct — this is the difference between
a product that has Tamil in it and a product that is set in Tamil. The **bilingual sign
block** (Tamil above, equal stroke weight from the same brush, one shared larger number
serving both lines, ward info small and red) is a complete, tested component spec that
Chennai's sign painters worked out empirically and most digital bilingual UIs get wrong.
The **1:12 palm-leaf band** and the **two-script convention** (rounded for vernacular,
angular for system) are free, high-leverage devices on top.

**Palette fit — neutral, which is the point.** Lampblack `#1b1815` ≈ `ink`; bleached leaf
`#e6dcc4` ≈ `alabaster`; the sharp/worn granite pair (`#6e6a63` / `#8a857c`) is a ready
active/disabled treatment. **Keep the signage yellow-and-red out of the product** — take
the *layout* rule from the street signs, not the colour.

**Ship first:** `:lang(ta)` metrics; the shared-number bilingual row.

---

## What to leave out

| Element | Why |
|---|---|
| Sunburnt-yellow facade field (§1.3) | The quarter's signature colour, but it fights brass and destroys the light editorial ground. Keep the green shutters instead. |
| Sign yellow `#efc031` / ward red (§6.3) | Too loud at any real area. 1–3% accent maximum, or marketing-page only. |
| Matrimandir golden-pink & four aspect colours (§3.3) | Saturated, spiritual-specific, and off-system. |
| Exact Sri Yantra (§4.2.5) | No agreed construction; a wrong one is worse than none. |
| Auroville spiral-arm pitch (§3.2.5) | **Unpublished.** Any spiral you draw is a reconstruction — label it. |
| Full bevelled prismatic lettering (§6.2.2) | One element only. As a system it reads as pastiche. |
| Kolam at any scale (§4.2.4) | The most recognisable Tamil motif and therefore the fastest route to looking like a tourist brochure. One instance per surface, low contrast. |
| Any figurative mural content | Out of scope by direction, and correctly so. |

---

## Sources

**Puducherry**
- INTACH Pondicherry, *Pondicherry Heritage Trail* map (published December 2007) — [PDF](http://intachpondicherry.org/flipbook/pdf/Heritage_Trail_Map_Pondicherry.pdf). *Primary source for all quoted facade and thinnai/thalvaram/mutram descriptions.*
- [INTACH Pondicherry — About Pondicherry](http://intachpondicherry.org/fr/About_pondy.php) (checkerboard plan; Franco-Tamil; heritage grading I / IIA / IIB / III; 1987–95 INTACH–EFEO inventory)
- [INTACH Pondicherry — About Us / FAQ](https://intachpondicherry.org/About_us_faq.php)
- [Puducherry Planning Authority — Building Bye-Laws and Zoning Regulations](https://www.naredco.in/notification/pdfs/PONDICHERRY%20Bye-law.pdf) *(read in full for heritage/colour clauses; clause 51(10) quoted)*
- [Pondicherry — Architecture in the French Quarter](https://peoplevillage.wordpress.com/2015/01/10/pondicherry-the-french-quarters-architecture/) (sunburnt yellow / peach / white; engaged columns; circular arched gates)
- [The Tamil Quarter in Puducherry — Paper Planes](https://www.joinpaperplanes.com/the-tamil-quarter-in-puducherry/)
- [Pondicherry Tourism — Heritage](http://www.pondytourism.in/puducherry-heritage.php)

**Auroville / Matrimandir**
- [Matrimandir — official site](https://matrimandir.org/matrimandir/) (inner chamber 12 m radius, 8.65 m walls, 15.2 m apex, 12 facets at 30°, 12 columns 60 cm; four pillar shapes and colours; 756 frames / 668 portholes; 216 lotus slabs)
- [Matrimandir — Technical Information, Auroville](https://auroville.org/page/matrimandir-technical-info) (1,415 discs; 954 convex @1.5 m; 461 concave @2.3 m; gold leaf 85×85 mm; lenses; crystal)
- [Matrimandir — The Park of Unity](https://matrimandir.org/the-park-of-unity/) (12 petals / 12 gardens names; amphitheatre dimensions; banyan)
- [The Amphitheatre — Auroville](https://auroville.org/contents/2140) (75 m / 98 m / 2.2 m; "family of circles whose centres are evenly spaced along a line which includes the Urn"; red Agra sandstone)
- [Matrimandir, Auroville — Archinomy](https://www.archinomy.com/case-studies/matrimandir-auroville/) (disc counts, column specs, 12 petals over 40 m)
- [The Galaxy Concept of the City — Auroville](https://auroville.org/page/galaxy-concept-of-the-city) (Crown; twelve radial roads; Lines of Force; Anger quote)
- [City Layout — Auroville](https://auroville.org/page/city-layout) and [Auroville in Brief](https://auroville.org/page/auroville-in-brief) (2.5 km city / 5 km with green belt)
- [Matrimandir — Wikipedia](https://en.wikipedia.org/wiki/Matrimandir) *(23.5 m height figure — conflicts with 29.5 m; see §3.1)*

**Madras Art Movement / Cholamandal**
- [Madras Art Movement — Wikipedia](https://en.wikipedia.org/wiki/Madras_Art_Movement) (calligraphic Malayalam-like forms, mathematical notation, astrological charts; artist styles; repoussé; batik/terracotta)
- [Madras Art Movement — Impart](https://imp-art.org/articles/madras-art-movement/) (line/colour/texture; abstract vs figurative rosters; kolam and craft sources)
- [K.C.S. Paniker — DAG](https://dagworld.com/k.c.s.paniker.html) (1963 onward; Klee; yantra; the shift to pinkish, foggy tonality)
- [The Cholamandal Canon — Open Magazine](https://openthemagazine.com/art-culture/the-cholamandal-canon) ("the line meets text which could be both legible or illegible"; Sultan Ali; Dhanapal/Nandagopal angular flat forms)
- [Words and Symbols — Google Arts & Culture](https://artsandculture.google.com/asset/words-and-symbols-k-c-s-paniker/uwGXowgK38dfKg)
- [Words and Symbols Series — Pundole's](https://auctions.pundoles.com/lots/view/1-6AZHFS/words-and-symbols-series) ("thin vertical and horizontal lines to cordon off space")
- [K.M. Adimoolam — Wikipedia](https://en.wikipedia.org/wiki/K._M._Adimoolam) · [S. Nandagopal — Wikipedia](https://en.wikipedia.org/wiki/S._Nandagopal)

**Kolam**
- [Kolam Simulation using Angles at Lattice Points — arXiv 2307.02144](https://arxiv.org/abs/2307.02144)
- [An algorithm for one-stroke kolam generation — npj Heritage Science](https://www.nature.com/articles/s40494-026-02310-3) (closed curve; one dot per bounded region)
- [Pulli Kolam: Method, meaning and mathematics — Sundari Silks](https://www.sundarisilks.com/blogs/article/tgif-motifs-pulli-kolam-method-meaning-and-mathematics)

**Typography & epigraphy**
- Aadarsh Rajan (EkType), *Finding Patterns and Rhythms in Tamil*, Typography Day 2016 — [PDF](https://www.typoday.in/2016/spk_papers/AadarshRajan_TypographyDay-2016.pdf). *Primary source for gate space, Pa-height, eye level, beak/mukka, four degrees of space, and the signage-painter method.*
- [November Tamil: Designing with Purpose — Typotheque](https://www.typotheque.com/articles/november-tamil-designing-with-purpose) (loops, tails, pa-height, Tamil/Latin sizing)
- D. Udaya Kumar, *Transformation of Tamil Letterforms from Palm Leaf Manuscripts to Early Letterpress Printing*, IDC, IIT Bombay — [profile](https://www.idc.iitb.ac.in/people/phd/uday-kumar-d)
- [Tamil handwritten palm leaf manuscript dataset (THPLMD)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10864864/) (4 cm × 48 cm average leaf)
- [What is Olai Chuvadi — Ancient Madurai](https://ancientmadurai.com/what-is-olai-chuvadi-palm-leaf-manuscript/) (stylus incision, lampblack, corner binding holes)
- [Inscriptions in Tamil Script — TN Dept. of Archaeology](https://www.tnarch.gov.in/epigraphy/inscriptions-tamil-script) (Tamil-Brahmi, Vatteluttu, Grantha chronology)
- [Reading Chola Tamil Inscriptions — Swaveda](https://www.swaveda.com/articles/chola-tamil-inscriptions-tracing-language-and-history-in-stone-338/) (rounded Tamil vs angular Grantha; register wear)
- Vidya Dehejia, *"Reading" Chola Temple Walls* — [PDF](https://vidyadehejia.com/wp-content/uploads/2023/10/Singapore-conference-3.-WAI_3-Dec_Vidya-Dehejia.pdf) *(could not be text-extracted; cited for base-moulding placement only, via secondary summary)*

**Public art & signage**
- [Street Signs of Chennai — Nia Murphy](https://cargocollective.com/niamurphy/Street-signs-of-Chennai) (black on yellow; Tamil above Latin; shared larger number; same brush, equal weight; red ward text; red arrow)
- [Hand-painted Signs: Forgotten Markers of the City Space — Sahapedia](http://www.sahapedia.org/hand-painted-signs-forgotten-markers-city-space) (bevelled prismatic lettering; satrangi seven-colour; tin → acrylic in the 1980s) *(article is Delhi-focused; technique generalises, city-specific claims do not)*
- [Once a publicity essential, banner culture has outlived its utility — The Federal](https://thefederal.com/states/south/tamil-nadu/once-a-publicity-essential-banner-culture-has-outlived-its-utility) (1948 *Chandralekha*; banner → vinyl)
- [Why posters and cut-outs in Tamil cinema are much more than advertisements — The News Minute](https://www.thenewsminute.com/tamil-nadu/why-posters-and-cut-outs-tamil-cinema-are-much-more-advertisements-132081) (gada cloth stitched; wooden frame; vajram gum + chalk water coat; oil coat; magic lantern transfer)
- [K. Mohan — Wikipedia](https://en.wikipedia.org/wiki/K._Mohan) (Mohan Arts, 1950)

---

*Compiled 2026-08-01. Research only — no repository code was modified.*
