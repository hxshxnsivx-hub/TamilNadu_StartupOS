# Tamil Nadu Art & Architecture Reference — for the Vanigam UI system

**Purpose.** Ground the ornament and structure of the Vanigam UI in genuine Tamil Nadu craft and architecture. This document is written for an engineer to implement from directly: every tradition gets a description, a *reproducible geometric construction*, a palette, and UI mappings.

**Scope note.** Figurative mural characters are deliberately out of scope. Everything here is non-figurative: geometry, rhythm, proportion, border structure, surface finish.

**Host palette this must sit with:**
| Token | Hex |
|---|---|
| Paper ground (alabaster) | `#f4f1ea` |
| Ink (warm near-black) | `#14120f` |
| Bottle green | `#1d3d33` |
| Antique brass | `#9a7b45` |

---

## CONFIDENCE LEGEND — read this before using any number

Colour and geometry claims are tagged. Do not silently promote a tag.

- **[SOURCED]** — the fact is stated in a cited source. Safe to rely on.
- **[DERIVED]** — I computed it from sourced numbers, or it is a standard mathematical description of a form the sources describe verbally (e.g. "rhombille tiling" for a described 3D-cube pattern). Reproducible, but it is my formalisation, not the tradition's own stated rule.
- **[PROPOSED]** — my design decision, made to be usable. Includes **every hex code in this document.**

> **Explicit caveat on all hex codes.** No source in this research gave hexadecimal or Lab/Munsell values for any traditional colour. Every hex below is my screen encoding of a *named* traditional colour (the names ARE sourced), tuned to sit next to `#f4f1ea` / `#14120f`. Treat the names as authoritative and the hexes as a starting proposal that a designer should revise against real photographs of tiles, silks and paintings. Do not present these hexes to anyone as "the traditional colour of X."

---

## 1. Athangudi Tiles — the primary pattern system

### What it actually looks like

Athangudi tiles (also called Chettinad or Karaikudi tiles) are handmade cement tiles produced in and around Athangudi village in the Chettinad region of Sivaganga district. They are unfired: coloured oxide slurry is hand-ladled into the compartments of a brass stencil resting on a **sheet of plate glass**, then backed with dry cement, then a wet mortar body; the tile air-cures 18–24 hours, water-cures 3+ days, then sun-dries. Total production time per tile is roughly 8–18 days. **[SOURCED]** The glass contact face is why the finished tile has a soft, slightly wavy, self-glazed sheen rather than a printed flatness — this is the single most characteristic quality and the one worth translating.

Standard sizes are **8″×8″ and 10″×10″**. **[SOURCED]** Designs fall into a small number of families: floral (lotus, jasmine, creeper), geometric (checkerboard, diamond, symmetrical arrangements), the **three-dimensional cube pattern** (usually black-and-white), the **Chokkattam pattern** (described in one source as "a six-shape unit design", after the traditional board game), plus dedicated **border tiles and corner tiles** that frame a field of plain or patterned tiles. **[SOURCED]** In the mansions, tiles run across courtyard floors and continue **up the wall to windowsill height**, with a different colour scheme per courtyard. **[SOURCED]**

Because the stencil is hand-poured and the pours bleed slightly at the boundaries, real Athangudi lines are **not crisp** — there is a visible 0.5–1.5 mm feather at every colour boundary, and no two tiles match exactly. This irregularity is the craft signature, not a defect.

### Concrete geometry

#### 1a. The cube pattern = rhombille tiling (highest-value, lowest-risk motif)

The "three-dimensional cube" pattern is mathematically a **rhombille tiling** (tumbling blocks). **[DERIVED — the name "3D cube pattern in black and white" is sourced; the formalisation as rhombille is mine, but it is the only tiling matching that description.]**

Construction, for rhombus edge length `s`:

```
Hexagon, pointy-top, circumradius = s, centre C at origin.
Vertices V_k at angle (90° + 60°k), k = 0..5, radius s.
Three rhombi per hexagon:
  R1 = C, V0, V1, V2
  R2 = C, V2, V3, V4
  R3 = C, V4, V5, V0
Each rhombus: all four sides = s; interior angles 120° at C, 60° at the outer vertex.
```

Lattice (hexagon centres):
```
a = ( s·√3 ,  0    )
b = ( s·√3/2, 1.5·s )
```
- **Symmetry group:** uncoloured rhombille is **p6m**; the three-tone cube colouring reduces it to **p3**. **[DERIVED]**
- **Suggested `s`:** 24 px at 1× (a 24 px rhombus gives a 41.6 px hexagon width — reads as texture, not as a graphic). Repeat tile: `41.57 × 36 px`, i.e. `<pattern width="41.569" height="36">` with the offset row handled by drawing two hexagons in the tile.
- **Three tones:** top face lightest, left face mid, right face darkest — or invert for a "punched" reading. Contrast ratio between adjacent faces should be kept **under 1.6:1** for a background texture; above ~2.5:1 it becomes a Op-art foreground and will fight your type.
- **Stroke:** traditional tiles have no outline — faces meet directly. If you need definition on a light ground, use a `0.5px` line at 8% ink rather than a hairline black.

#### 1b. The 4-tile rosette rule (tile framing)

Standard practice for encaustic/handmade cement tiles, including Athangudi: the motif in each tile corner is a **quarter** of a larger rosette, so a 2×2 block of identical tiles completes four full rosettes at the tile intersections. **[DERIVED — the source confirms "a composition of tiles used together" and the existence of border/corner tiles; the quarter-rosette mechanic is the standard cement-tile convention, not separately confirmed for Athangudi in this research. Flag if precision matters.]**

Proposed module **[PROPOSED]**, modelling 8″ at 12 px/inch:
```
T          = 96 px          tile edge
border     = T/8  = 12 px   outer band
field      = 72 px          inner field
corner arc = T/4  = 24 px   quarter-rosette radius
repeat unit = 2T × 2T = 192 px, symmetry p4m (or p4g if the motif is chiral)
```

#### 1c. Field / border / corner grammar

An Athangudi floor is composed, not tiled uniformly: a **field** of one pattern, a **border band** of 1–2 tile courses in a different pattern running the room perimeter, and dedicated **corner tiles** that turn the border correctly. **[SOURCED]** This is a directly transferable layout rule (see UI mapping).

### Palette

Two sourced colour sets, which conflict slightly — report both.

Set A, "standard colours": **red, mustard, green, grey** **[SOURCED — Google Arts & Culture / Dastkari Haat Samiti]**
Set B, common combinations: **red, blue, yellow, white, black** **[SOURCED — Paper Planes]**
Also cited for the "Chettinad traditional" family: red, yellow, green, indigo. **[SOURCED]**

Union, with proposed hexes **[PROPOSED hexes]**:

| Name | Hex | Note |
|---|---|---|
| Oxide red | `#9C3B2E` | iron-oxide red, the dominant Athangudi colour |
| Mustard / ochre | `#C08A2E` | close cousin of your existing brass `#9a7b45` |
| Tile green | `#3D6B4A` | lighter and greyer than your bottle green |
| Indigo | `#2C4670` | |
| Cement grey | `#8C8B84` | the unpigmented body colour |
| Lime white | `#EDE7D9` | almost your paper ground — good, means Athangudi sits natively on `#f4f1ea` |
| Oxide black | `#1E1B18` | |

**Design read:** this palette is *desaturated earth over a warm white*. It is already compatible with the Vanigam ground. Use at most two chromatic oxides plus white per surface — real tiles rarely exceed 3–4 colours because each colour is a separate hand pour.

### How it could serve a UI

- **Background tiling** — rhombille at 8–12% opacity ink as a whole-page or panel texture. This is the single strongest candidate.
- **Section dividers** — a single course of "border tile" pattern, 12–16 px tall, full-bleed, between major page sections.
- **Card frames** — the border/field/corner grammar maps exactly: card = field, 12 px inset border band, and a distinct corner treatment where the band turns.
- **Empty states** — a large, low-contrast single tile motif (one 192 px 4-tile rosette) centred, at 6% ink.
- **Loading states** — reveal a rhombille field rhombus-by-rhombus in the p3 rotational order; reads as a floor being laid.
- **Dashboard grid** — the 8″ module → an 8-column or 96 px baseline grid, with the "field vs border" idea used to distinguish content zones from chrome.

---

## 2. Chettinad Mansion Architecture

### What it actually looks like

A Chettinad mansion is organised as a **single east–west axis** through a sequence of **diminishing courtyards**, so that from the front door you can see straight through to the back. **[SOURCED]** The named plan sequence is: **Mugappu** (entrance/reception) → **Valavu** (first courtyard, the main living court, with four corner platforms called *pattalai*) → **Irandankattu** (second block) → **Moonamkattu** (third block) → **Thottam** (garden/rear). **[SOURCED]** Elements are laid out in **binary symmetry about the axis** — colonnades, small rooms and steps mirror left and right. **[SOURCED]** At the street edge sits the **thinnai**, a raised masonry platform under the entrance verandah, used as reception and as the merchant's place of business. **[SOURCED]**

Each courtyard is ringed by a colonnaded verandah; columns are **Burma teak, granite, or marble**, richly carved, and column richness was an explicit display of wealth. **[SOURCED]** Teak imported from Burma and Ceylon was used for roofing and columns. **[SOURCED]** Walls are finished with a **lime-and-egg-white plaster** that has held a satin sheen for over a century; floors use polished lime plaster or Athangudi tile. **[SOURCED]** Courtyards flood the centre with light while the deep verandahs leave the surrounding rooms in cool shadow — a **high-contrast core, low-contrast periphery**. **[SOURCED]**

> **Uncertainty:** I found no source giving canonical column spacing, courtyard aspect ratio, or storey heights in numbers. Any specific ratio below is marked [PROPOSED].

### Concrete geometry

**The diminishing-court rule** — the most valuable structural idea here. **[PROPOSED formalisation of a SOURCED phenomenon: "a series of inner courtyards, each a diminishing rectangle of light".]**

```
Court widths along the axis:  W_n = W_0 · r^n,   r ≈ 0.8,  n = 0,1,2
e.g. 100% → 80% → 64%
```
Directly usable as a **vertical rhythm** for a page: hero band, then each successive section 80% of the previous section's vertical padding. Gives a page that visibly settles as you scroll.

**Colonnade rhythm** **[PROPOSED]**:
```
column bay pitch  p
column shaft width  = p/6
verandah depth      = p        (square bay)
courtyard opening   = odd number of bays (5, 7, 9) so a column never sits on the axis
```
The odd-bay rule is a direct consequence of the sourced binary symmetry — an even count would put a column on the centreline and break the through-view.

**Egg-plaster surface** **[DERIVED from sourced description]** — the visual character is a *satin, not gloss*: a very broad, very low-amplitude specular. In CSS this is **not** a box-shadow; it is a large-radius, very low-alpha linear gradient over a warm white, plus a fine grain:
```
background:
  linear-gradient(160deg, rgba(255,255,255,.55), rgba(255,255,255,0) 60%),
  <1.5% ink noise>,
  #f4f1ea;
```

### Palette

| Name | Hex | Note |
|---|---|---|
| Egg-lime plaster | `#EFEADC` | **[PROPOSED]** the wall ground; warmer and lighter than `#f4f1ea` |
| Burma teak | `#6B4423` | **[PROPOSED]** |
| Teak, aged/oiled | `#3E2A18` | **[PROPOSED]** |
| Granite column grey | `#6E6A63` | **[PROPOSED]** |
| Shadowed verandah | `#241F19` | **[PROPOSED]** the deep-shade value |
| Mangalore tile red | `#A8503A` | **[PROPOSED]**; sourced as a Chettinad/Coimbatore roof material |

### How it could serve a UI

- **Grid system** — odd-bay colonnade → 5/7/9-column layouts with a true centre column. Unusual, and it makes centred editorial layouts structurally honest rather than accidental.
- **Vertical rhythm** — the diminishing-court ratio `r = 0.8` for section spacing.
- **Page architecture** — mugappu (hero/entry) → valavu (primary workspace, brightest, highest contrast) → successive kattu (progressively quieter sections) → thottam (footer). This is a genuinely Tamil information architecture, and it is nameable in product copy.
- **Light model** — bright centre, dark deep edges. Cards at the page centre get the paper ground; peripheral chrome (nav, sidebars) gets the shadowed-verandah value. Inverts the usual "dark canvas, light card" convention in a defensible way.
- **Surface finish** — the egg-plaster satin as the default card background instead of flat white.
- **Thinnai** — a raised, bordered platform at the top of a page or card: the "business is done here" zone. Good for the primary CTA block.

---

## 3. Kolam / Padi Kolam Geometry

### What it actually looks like

A kolam is drawn each morning on the threshold in rice flour. A grid of dots (**pulli**) is laid down first; a continuous line (**kambi**) is then drawn *around* the dots — never through them — until every dot is enclosed and the line closes on itself. **[SOURCED]** The **sikku kolam** (knot kolam) / **kambi kolam** (wire kolam) is the interlaced single-loop variety. **[SOURCED]**

Two dot-grid families: **ner pulli** (aligned rows — e.g. a 15-to-1 pattern with rows of 15, 13, 11, 9, 7, 5, 3, 1 on each side of a central row) and **idukku pulli** (interlaced — each row offset to sit *between* the dots of the row above). **[SOURCED]**

Visually: thin, even-weight white line on a dark ground, all turns rounded, no line ever terminates, and the whole figure has reflective and/or rotational symmetry. It reads as a *single knot*, not a drawing. This is the most conceptually apt motif for a startup OS — one unbroken line enclosing many separate points.

### Concrete geometry — the three laws

**[SOURCED — Nagata/Thamotharan et al., arXiv:2304.14134]**
1. Every dot is individually encircled by the line.
2. Line crossings are discrete points (transversal, never tangential, never overlapping runs).
3. There are no loose ends.

Plus **[SOURCED]**: never trace the same route twice; straight segments run on a dual grid inclined at **45°** to the dot grid; arcs are drawn surrounding the dots. And the practitioner's rule that mathematically guarantees a single continuous loop: **every vertex must have even degree** (Eulerian circuit). **[SOURCED]**

### Concrete geometry — the lattice/angle method (best for programmatic generation)

**[SOURCED — arXiv:2307.02144, "Kolam Simulation using Angles at Lattice Points"]**

```
Dot grid spacing            = L·√2
Dual lattice unit cell side = L        (rotated 45° w.r.t. the dot grid)
Movement is always along dual-cell edges, in steps of length L.

Four permitted directions:
  a =   45°
  b =  135°
  c =  -45°
  d = -135°

A kolam == a finite sequence over {a,b,c,d}, unique up to cyclic permutation.

Shape emitted depends on the number of consecutive direction changes:
  Shape I    0 changes   straight continuation
  Shape II   1 change    single turn,  spanning 2L
  Shape III  2 changes   double turn,  spanning 3L
  Shape IV   3 changes   triple turn,  spanning 4L
```

Implementation note: this is a turtle over a 45°-rotated lattice. Encode a kolam as a string over `abcd`, render with four path primitives. For a design system, pre-render 8–12 curated sequences rather than generating live.

### Concrete geometry — the L-system (best for animation)

**[SOURCED — IMAGINARY, "MathLapse: L-System for Single Knot Kolam Pattern Generation"]**

```
Alphabet : F, A, B
Axiom    : FBFBFBFB
Rules    : A → AFBFA
           B → AFBFBFBFA
Turn     : 45°

Turtle interpretation:
  F : forward 10 units, drawing
  A : arc, radius 10, sweep 90°
  B : d = 5/√2 ; forward d ; arc sweep 270° ; forward d
```
Iterating produces successively larger single-knot (anthathi) kolams. The resulting graph is Eulerian — one continuous line, every edge traversed once. **[SOURCED]** This is ideal for a loading animation: animate `stroke-dashoffset` along the single path and the line literally draws itself the way a kolam is drawn.

### Concrete geometry — minimal single-dot unit

**[DERIVED — my parametric formalisation; not from a cited source. Use for ornament, not as a claim about tradition.]**

For dot pitch `d`, a single enclosed pulli:
```
Dot:   circle, r = 0.06·d, filled
Loop:  diamond with vertices (±0.5d, 0), (0, ±0.5d)
       each of the 4 sides replaced by an outward-bulging circular arc
       with sagitta 0.10·d
Stroke: 0.05·d, round cap, round join
```
Four of these sharing arcs give the classic 2×2 knot.

**Grid construction for a ner pulli field:**
```
Rows of odd counts, symmetric:  1, 3, 5, …, N, …, 5, 3, 1
Row pitch = dot pitch = d
Row i horizontal offset = (N − count_i)/2 · d
```
**Idukku pulli:** each successive row offset horizontally by `d/2`. **[SOURCED]**

**Stroke weight:** kolam line is even-weight throughout. For UI use `1px` at 1×, `1.5px` at 2× — thinner than you think. A kolam drawn with a heavy stroke reads as a logo, not a kolam.

### Palette

Kolam is essentially **monochrome**: white rice flour on a swept, water-darkened earth threshold; coloured *kolam podi* is a later, festival-specific variant.

| Name | Hex | Note |
|---|---|---|
| Rice flour white | `#FBF8F0` | **[PROPOSED]** |
| Wet threshold earth | `#2A231C` | **[PROPOSED]** |
| Red oxide threshold band (*kaavi*) | `#8E4A33` | **[PROPOSED]** — the ochre band often edging the threshold |

**Design read:** kolam should be your *monochrome* system. Resist colouring it. Its whole power is one line, one value.

### How it could serve a UI

- **Loading states** — the single best fit anywhere in this document. A self-drawing single-knot kolam via `stroke-dashoffset`, using the L-system path. It is thematically exact: one continuous line, no loose ends, completed only when every point is enclosed.
- **Empty states** — a dot grid with no line yet ("nothing enclosed yet"), which resolves into a kolam when the first item is created. This is a genuinely good product metaphor for a founder platform.
- **Progress / onboarding** — n steps = n pulli; the line encloses one more dot per completed step.
- **Section dividers** — a single row of the sikku knot, 24 px tall, repeated horizontally.
- **Favicon / mark** — a 1-dot or 4-dot knot.
- **Grid systems** — the 45° dual grid as an alternative diagonal alignment for decorative overlays.

---

## 4. Coimbatore Central Library & Coimbatore Town Hall

### Honest assessment first

**Sources are thin, and unevenly so.** The Town Hall is documented. **The Central Library is essentially undocumented architecturally.** I recommend **not** deriving UI language from the library at all. Do not let anyone fill the gap with invention.

### Victoria Town Hall, Coimbatore (1892) — [SOURCED]

Neoclassical civic building on Bazaar Street, inaugurated 1892, built for ₹10,000 to commemorate Queen Victoria's golden jubilee (campaign led by S. P. Narasimhalu Naidu from 1887). Constructed footprint ~6,000 sq ft including a 3,000 sq ft main council hall; two floors plus a **wooden mezzanine visitors' gallery** overlooking the assembly space. **Large arches in Gothic form supported on Greek-order columns** lead to the foyer; the main hall is flanked on three sides by corridors on **large Tuscan columns**. **Large timber roof trusses**; roof of **red Mangalore tiles** (hard laterite clay); **stone walls plastered with lime mortar**. Seat of the Coimbatore Municipal Corporation since 1992; renovated 2022.

A separate **clock tower (1877)**, donated by the family of A. T. Thiruvenkataswamy Mudaliar, stands near the Town Hall on Big Bazaar Street. **[SOURCED]**

**No murals, reliefs, or decorative public artwork are documented in any source I found.** The building's visual character is structural, not ornamental: arch rhythm, Tuscan colonnade, and a red tile roof over lime-white walls.

### Coimbatore District Central Library — [SOURCED but minimal]

Service began 1952 at the Victoria Town Hall; moved mid-1956 to the Gandhi Memorial Library building at VOC Park; subsequently moved to its present building at No. 50, Cowley Brown Road, R. S. Puram. The current building is a multi-storey structure with a carpet area of ~21,453 sq ft.

**That is the entirety of what I could source.** No architect, no style attribution, no facade description, no murals or reliefs. **Recommendation: exclude from the design language.** If this building matters to the brief for civic-legitimacy reasons, the honest path is a site visit / photographs, not desk research.

### Concrete geometry — what is usable

Only one thing, from the Town Hall **[DERIVED from the sourced description]**: a **Tuscan colonnade with round-arched openings**, which is a clean, restrained arcade rhythm:
```
Tuscan proportion (canonical): column height = 7 × shaft diameter D
Arcade bay:  pier centres at 4D
             arch springing at 5D above base
             semicircular arch, radius 1.5D  (clear opening 3D)
Entablature depth ≈ 1.75D
```
> **[DERIVED]** The 7D Tuscan ratio is the standard classical order, not a measured value from this specific building.

### Palette (from sourced materials only)

| Name | Hex | Note |
|---|---|---|
| Lime-plaster white | `#EFEADC` | **[PROPOSED]** |
| Mangalore tile red | `#A8503A` | **[PROPOSED]** |
| Timber truss brown | `#5A3E28` | **[PROPOSED]** |

### How it could serve a UI

Low priority. If used at all: the arcade rhythm as a **header/nav treatment** (repeating round-arch bays as nav item separators), or the mezzanine-gallery idea as a **sticky secondary rail overlooking a main content well**. Nothing here is distinctive enough to carry brand weight — the Town Hall is colonial neoclassical, present in every Indian district capital.

---

## 5. Temple Architecture Geometry — proportion and stepped form

### What it actually looks like

A Dravidian temple presents two stepped pyramidal forms: the **vimana** over the sanctum, and the far larger **gopuram** gateway towers in the enclosure walls. Both are built of stacked horizontal tiers called **tala**, each tier a complete miniature storey — a wall zone with slender pilasters, crowned by a parapet — and each successively smaller, producing the stepped taper. **[SOURCED]** Vimanas are classified by tier count: *ekatala* (1), *dvitala* (2), *tritala* (3), up to thirteen at Srirangam. **[SOURCED]**

The parapet of each tala — the **hara** — is not a plain band. It is a row of miniature shrines (**aedicules**): square domed **kuta** at the corners, barrel-vaulted **sala** at the centres of the sides, and small barrel-roofed **panjara** niches between, linked by recessed connecting stretches (*harantara*). **[SOURCED — Adam Hardy, *Indian Temple Architecture: Form and Transformation*]** The result is a rhythm, repeated at every level: **kuta – panjara – sala – panjara – kuta**.

Pallava rock-cut work at Mahabalipuram supplies the ancestral vocabulary in its cleanest, most legible form: **kudu** (horseshoe/chaitya dormer arches) running the full length of the **kapota** cornice above the pillars, barrel-vaulted *shala* roof forms on the architraves, and pillars with lion bases. **[SOURCED]** The monuments are rock-cut cave mandapas, monolithic rathas, bas-relief panels, and structural temples. **[SOURCED]**

Measurement itself is proportional: **tala** is also a unit (the palm, wrist to fingertip), subdivided into **12 angula**; the whole building is dimensioned in these body-derived units rather than absolute ones. **[SOURCED]**

### Concrete geometry — measured gopuram numbers [SOURCED]

Meenakshi Amman Temple, Madurai:

| Gopuram | Talas | Height | Base | H : base-width | Base aspect |
|---|---|---|---|---|---|
| East (over Sundareswarar sanctum) | 9 | 153.3 ft | 111.3 × 65.6 ft | 1.38 | 1.70 : 1 |
| Tallest (as reported) | 9 | 160.9 ft | 108 × 67 ft | 1.49 | 1.61 : 1 |
| Chittirai | 7 | 177 ft | 78 × 38 ft | 2.27 | 2.05 : 1 |
| West | — | 163.25 ft | — | — | — |

> **SOURCE CONFLICT — flagging explicitly.** The same body of sources calls a 9-tier gopuram "the tallest" at 160.9 ft while also giving the 7-tier Chittirai gopuram as 177 ft. These cannot both be right. Treat individual figures as indicative, not exact. What *is* robust across all of them: **height-to-base-width sits in the 1.4–2.3 range, and the base is a rectangle of roughly 1.6–2.0 : 1.**

**Usable proportion rule [DERIVED]:** `H ≈ 1.5 × base width` for a broad 9-tala gopuram; the base footprint is `~1.7 : 1`. For a UI hero or masthead, `1.5 : 1` (height : width) is a distinctive, non-generic aspect that is genuinely grounded.

### Concrete geometry — the stepped taper

> **Gap, stated plainly:** I found **no** source giving a canonical batter angle or a prescribed tier-diminution ratio for gopurams. The literature I reached describes the taper only qualitatively ("decreasing in size upward"). The rule below is **[PROPOSED]** — a geometric series chosen because it produces the characteristic slightly-concave gopuram silhouette. It is *not* a traditional prescription.

```
For n talas, with r = (w_top / w_base)^(1/n):

  w_k = w_base · r^k        tier width
  h_k = h_0   · r^k         tier height (tiers get shorter as they narrow)

Recommended: w_top / w_base = 0.50
  n = 5  →  r = 0.871
  n = 7  →  r = 0.906
  n = 9  →  r = 0.926
  n = 13 →  r = 0.948
```
Because both width and height shrink by `r`, the accumulated height converges — which is exactly why a 13-tala tower is not proportionally much taller than a 9-tala one. The profile is a stepped concave curve, not a straight-sided triangle. **This is the key visual: gopuram silhouettes are concave, never straight.**

### Concrete geometry — the hara rhythm (highly implementable)

**[DERIVED formalisation of the SOURCED kuta/sala/panjara sequence]**

For a parapet of run length `W`:
```
Sequence:  kuta – panjara – sala – panjara – kuta      (5 elements, mirror-symmetric)
Widths as fractions of W:
  kuta    (square, domed)        0.18   × 2 = 0.36
  panjara (small barrel niche)   0.11   × 2 = 0.22
  sala    (barrel vault, centre) 0.26
  harantara (recessed links)     0.16 total, 4 × 0.04
Element heights: sala = 1.0h, kuta = 0.92h, panjara = 0.62h
Recesses sit 0.25h lower than the aedicule tops.
```
This gives an **A B C B A** silhouette — a dense, symmetric, non-figurative band. It is one of the best divider candidates in this document because it is instantly South Indian without being religious imagery.

### Concrete geometry — the kudu (horseshoe arch)

**[DERIVED parametrisation of the SOURCED form]**

A kudu is a horseshoe arch: a circular arc of **more than 180°**, so the opening is narrower than the arch's widest point.
```
Circle centre O, radius R.
Arc swept from 210° to −30° passing through 90°  → 240° of arc.
Springing points at angle 210° and −30°:
   ( −R·cos30°, −R·sin30° ) and ( R·cos30°, −R·sin30° )
Vertical jambs drop from the springing points to the base line, length 0.6R.
Total kudu height = R + R·sin30° + 0.6R = 2.1R
Clear opening width = 2R·cos30° = 1.732R
Max arch width      = 2R
Stroke / moulding depth = 0.12R
```
Kudus are repeated **continuously along the whole length of a cornice** **[SOURCED]** at a pitch of `2.4R` **[PROPOSED]** — i.e. touching-but-not-overlapping, with a narrow flat between.

### Palette

Sourced materials only: granite (Pallava and Chola work), lime plaster, and the polychrome *sudhai* (lime-stucco) figures on later gopurams — which are exactly the figurative content you are excluding, so ignore their colour.

| Name | Hex | Note |
|---|---|---|
| Charnockite / Mahabalipuram granite, dry | `#8A8378` | **[PROPOSED]** |
| Granite, weathered / lichened | `#6E6A5C` | **[PROPOSED]** |
| Granite, wet / shadowed | `#3D3A34` | **[PROPOSED]** |
| Lime whitewash | `#EDE8DA` | **[PROPOSED]** |

**Design read:** if you use temple geometry, use it in **stone values only** — greys and lime white. The polychrome gopuram is a 17th-century-onward surface treatment and it will read as kitsch on screen. Stone reads as architecture.

### How it could serve a UI

- **Section dividers** — the hara rhythm (kuta–panjara–sala–panjara–kuta), 20–28 px tall, at 15% ink. Strongest divider candidate.
- **Card frames / headers** — the kudu arch as a repeating cornice band along a card's top edge, at very low contrast.
- **Hierarchy model** — the tala system is a *literal* visual hierarchy: each level is a complete, smaller repetition of the level below. Map it to nested content: a section, its subsections, and their cards each use the same frame at `r = 0.9` scale. This is a rare case where an ornamental system encodes a genuine information-design principle.
- **Proportion** — `1.5:1` hero aspect; base footprint `1.7:1` for feature cards.
- **Progress / levels** — n-tala stack as a progress indicator for a multi-stage founder journey (idea → incorporation → funding → scale). Each completed stage adds a tier. Concave taper means later stages are visually narrower and more precious.
- **Loading** — build the tala stack bottom-up.

---

## 6. Temple Car (Ther) Woodwork & Tanjore Painting

These two belong together: both are **gilded, framed, jewelled, high-relief** traditions, and both supply *framing* rather than *field* language.

### 6a. Temple car (ther) woodwork

**What it looks like.** A temple chariot is effectively a **portable vimana in wood on 4–8 massive wheels**, carrying the processional deity through the streets. **[SOURCED]** Carving runs 1–8 metres in height and is composed of **multiple set-in panels** — discrete rectangular framed fields — containing yaali and makara (mythical beasts), animals, ganas, dancers, and decorative floral motifs. **[SOURCED]** The Thiruvarur *Aazhi Ther* at the Thyagaraja temple is Asia's largest, ~96 ft (30 m) tall when fully dressed, ~350 tonnes, carved by hereditary artisans called **Kothanars**. **[SOURCED]** Related and separately GI-tagged: **Kallakurichi wood carvings** (Tamil Nadu). **[SOURCED]**

The transferable idea is the **set-in panel**: the entire surface is subdivided into a strict rectangular grid of framed, recessed fields, each containing one motif. It is a card system, six centuries old.

**Concrete geometry [DERIVED]:**
```
Panel grid on a tiered stack. For a stack of tiers of height H_t:
  panel aspect      2 : 3  (portrait) for figure panels
                    3 : 1  (band)     for floral/creeper registers
  frame moulding    0.06 × panel width, three-step profile
                    (fillet 0.02 / ovolo 0.025 / fillet 0.015)
  recess depth      0.04 × panel width
  gap between panels 0.10 × panel width — panels never touch
Registers alternate: figure register / narrow floral band / figure register.
Tiers diminish upward by r ≈ 0.85.   [PROPOSED]
```

**Palette:**

| Name | Hex | Note |
|---|---|---|
| Unpainted seasoned teak | `#6B4423` | **[PROPOSED]** |
| Aged/oiled carving | `#3E2A18` | **[PROPOSED]** |
| Vermilion trim | `#B03A2E` | **[PROPOSED]** |
| Gilt highlight | `#B08D3F` | **[PROPOSED]** — near your brass `#9a7b45` |

### 6b. Tanjore (Thanjavur) painting

**What it looks like.** Cotton cloth mounted on a wood board; relief built up in **gesso** (traditionally limestone/chalk powder with gum arabic or tamarind seed paste), applied with a fine brush or pointed tool to raise the jewellery, crowns, garments, and — critically for us — the **architectural arch, the *prabhavali***. **[SOURCED]** **22-carat gold leaf** is laid over the gessoed relief (22ct specifically: 24ct is too soft and tears, lower carats lose the colour). **[SOURCED]** **Jaipur stones** (semi-precious) and cut glass are set into the gold. **[SOURCED]** Backgrounds are flat, saturated, and deep — **crimson, emerald green, or dark blue** — chosen so the gold jumps forward. **[SOURCED]** Borders are often intricate floral bands, also gessoed. **[SOURCED]**

The transferable ideas: (i) **a small raised, gilded frame around a flat saturated field**; (ii) **the prabhavali arch as the canonical framing device**; (iii) **jewel points** — small, discrete, high-brilliance accents on an otherwise matte surface.

**Concrete geometry [DERIVED]:**

Prabhavali arch frame, for an opening of width `W`:
```
Springing height        = 0.55 W above base
Arch: semicircle radius = 0.50 W, centred on the springing line
Frame band thickness    = 0.09 W
Gesso relief height     = 0.012 W        (in UI: a 1–2px highlight/shadow pair)
Makara terminals at the two springing points: bosses of radius 0.07 W
Jewel points: radius 0.018 W, spaced along the arch centreline
              at 15° intervals of arc  →  13 stones over 180°
Inner field: flat, unmodulated saturated colour. No gradient. This matters.
```

Gesso-relief in CSS **[PROPOSED]** — the look is a *hard, shallow, doubled* edge, not a soft drop shadow:
```
box-shadow:
   inset 0 1px 0 rgba(255,255,255,.45),
   inset 0 -1px 0 rgba(0,0,0,.28),
   0 1px 0 rgba(0,0,0,.18);
border: 1px solid #9a7b45;
```

**Palette:**

| Name | Hex | Note |
|---|---|---|
| Gold leaf, 22ct (mid) | `#B8912F` | **[PROPOSED]**; sits beside your brass `#9a7b45` |
| Gold leaf, highlight | `#E3C572` | **[PROPOSED]** |
| Gold leaf, shadow | `#7A5E22` | **[PROPOSED]** |
| Ground: crimson | `#8C1D2C` | **[PROPOSED]** — sourced as "deep crimson" |
| Ground: emerald | `#0F5132` | **[PROPOSED]** — sourced as "emerald green"; close to your `#1d3d33` |
| Ground: dark blue | `#1B2A6B` | **[PROPOSED]** — sourced as "dark blue" |
| Gesso white | `#F2EDE3` | **[PROPOSED]** |

**Design read:** Tanjore is your **premium / achievement** register, and it must be used sparingly. Its whole logic is *a small amount of gold against a large amount of flat deep colour*. The failure mode is gold everywhere — which reads instantly as a cheap wedding invitation. Gold coverage on any surface should stay under ~5% of area.

### How they could serve a UI

- **Card frames** — the ther set-in panel grid (framed, recessed, never touching) is a directly usable card system with real provenance.
- **Achievement / milestone states** — Tanjore gesso-and-gold frame around an otherwise ordinary card. Reserve for funding rounds closed, cohort graduation, verified status.
- **Section dividers** — the narrow floral register band from ther woodwork, 3:1 aspect, at low contrast.
- **Empty states** — an empty prabhavali arch: the frame with nothing in it. Literally "the frame is ready."
- **Badges** — jewel points (small circles at 15° intervals) as a rating or completion indicator on a curved track.
- **Dark-mode accent** — the three Tanjore grounds (crimson/emerald/blue) are the only truly saturated colours in this whole document. If Vanigam ever needs a dark surface, these are the sourced options.

---

## 7. Kalamkari & Kanchipuram Silk — border (korvai) structures

### 7a. Kalamkari — with an important correction

> **CORRECTION, stated up front.** The two famous Kalamkari centres — **Srikalahasti** (pen/*kalam* work) and **Pedana/Machilipatnam** (block-printed) — are in **Andhra Pradesh, not Tamil Nadu.** If Vanigam's brief is specifically Tamil Nadu craft, the Andhra centres are the wrong citation.
>
> **The correct Tamil Nadu tradition is Karuppur Kalamkari**, which received a **GI tag in October 2021** (application by the Tamil Nadu Handicrafts Development Corporation, Poompuhar). It is practised in **Karuppur and surrounding villages, Udayarpalayam taluk, Ariyalur district**, and around **Sickhanayakanpatti / Sikkalnaikkanpettai and Thirupanandal, Thiruvidaimarudur taluk, Thanjavur district**. **[SOURCED]**

**What Karuppur kalamkari looks like.** Dye-painted figurative and patterned cloth made **for temple use**: ceiling cloths, **thombai** (cylindrical hangings), **thoranam** (door hangings/festoons), umbrella covers and chariot covers. Motifs include yaali, peacock, swan (*annam*), flowers, and deities. Drawn with pens/brushes made from bamboo and coconut stems. **[SOURCED]**

**The single most useful fact in this section: traditionally only THREE colours are used — black, red and yellow.** **[SOURCED]** That is a genuinely restrained, GI-documented Tamil Nadu palette, and it is unusually well suited to an editorial UI.

**Process (Srikalahasti method, for context — [SOURCED]):** up to 23 steps over 15–20 days; cotton softened with cow dung and bleach; base mordant of **myrobalan** (*Terminalia chebula*) tannin, which gives the ground its warm buff cast; outlines in **kasimi / kasim kaaram** (iron acetate, iron scraps fermented in jaggery water for ~21 days); red from **alizarin/madder** reacting with pre-painted alum; blue from **indigo**; yellow from **pomegranate rind and turmeric**; green from indigo over yellow. **Buffalo milk** (not cow's) is applied to the cloth first — its higher fat content creates a hydrophobic barrier that stops the dye wicking, which is what permits the razor-sharp line. **[SOURCED]**

**Concrete geometry — the thoranam border [DERIVED]:**

A thoranam is a hung festoon — the archetypal Indian "top of section" ornament, and a natural web divider.
```
Run length W, hang depth D = 0.10 W.
Scallop pitch p = D · 1.6
Each scallop: circular arc, radius 0.5p, sagitta 0.55·(0.5p)   (slightly deeper than semicircular)
Cusps between scallops carry a pendant: teardrop, height 0.45D, width 0.18p
Top edge: straight rail, stroke 0.05D
Every 5th scallop: substitute a larger pendant (mango/leaf), height 0.75D
```

**Palette (Karuppur three-colour, plus the Srikalahasti extensions):**

| Name | Hex | Confidence |
|---|---|---|
| Kalamkari black (*kasimi*, iron acetate) | `#1C1A17` | **[PROPOSED]** hex; three-colour rule **[SOURCED]** |
| Kalamkari red (alizarin / madder + alum) | `#9E3B2E` | **[PROPOSED]** hex |
| Kalamkari yellow (pomegranate rind / turmeric) | `#C9A227` | **[PROPOSED]** hex |
| Myrobalan ground (buff cream) | `#E8DFC8` | **[PROPOSED]** hex |
| Indigo (*neelam*) — Srikalahasti, not Karuppur | `#26456B` | **[PROPOSED]** hex |
| Indigo-over-yellow green | `#4A6B3A` | **[PROPOSED]** hex |

### 7b. Kanchipuram silk

**What it looks like.** A Kanchipuram saree is composed of four named parts: **body**, **border**, **pallu** (the decorated end), and **buttas** (scattered motifs). **[SOURCED]** In the **korvai** technique, body and border are woven **in different colours as physically separate fabrics on the same loom** — two artisans weaving in tandem, three shuttle passes each — and mechanically **interlocked** at the join, which both strengthens and sharpens the boundary. Where the pallu differs in colour it is joined by korvai or *petni*. **[SOURCED]**

This is the crucial structural idea, and it is unusual: **the border is not applied to the body — it is a different fabric, interlocked.** The colour change is absolute and load-bearing. There is no gradient, no fade, no shared thread. Translated to UI: **a hard, structural, contrast-coloured edge that is part of the construction, not a decoration on top of it.**

**Motifs [SOURCED]:** *mayil* (peacock), *maanga*/mango butta, *annam* (swan), *rudraksham*, floral vines, yaali, and the **temple border** — small triangular forms, locally also called *muggu*, resembling gopuram silhouettes, repeated along the interlocking border. Zari (metallic thread) does the line work; pallu carries heavier zari than the body. **[SOURCED]** Proportion convention: a **plain or lightly-buttaed body against an ornate, heavy border and pallu**. **[SOURCED]**

**Concrete geometry — temple border (*muggu*) [DERIVED]:**
```
Base pitch b. Triangle: isosceles, base b, height 0.85b.
Row 1: triangles at pitch b along the border's inner edge, apices pointing into the body.
Row 2 (optional, common): identical triangles offset horizontally by b/2 and
        vertically inward by 0.35b, in a second colour — producing the
        characteristic stepped/serrated double edge.
Zari outline: stroke 0.05b, applied only to the leading edge of each triangle.
Recommended b: 12–16 px.
```

**Concrete geometry — korvai border proportion [DERIVED from sourced convention]:**
```
Border width  : body width  =  1 : 6   (a 6" border on a 45" panel)
Pallu depth   : total length =  1 : 8
Butta pitch in the body: 5–8 × butta diameter — buttas are sparse; the body is mostly ground.
Colour rule: border hue is a hard contrast to the body (classic pairing: deep red body / bottle green border, or the reverse).
```

**Palette — traditional Tamil colour names [names SOURCED, hexes PROPOSED]:**

| Tamil name | Meaning | Hex |
|---|---|---|
| **Arakku** (அரக்கு) | lac resin — deep crimson-maroon; the bridal colour | `#7B1E28` |
| **Mayilkazhuthu** (மயில் கழுத்து) | peacock's neck — iridescent blue-green | `#0E5A63` |
| **Manthulir** | tender mango leaf — a *shot* colour, green shot with red | warp `#3F5E23` / weft `#7A2E2E` |
| **Pattu roja** | garden rose pink, from bridal garlands | `#D4738C` |
| **Kesari** | saffron | `#E08A1E` |
| **Naval pazham** | java plum | `#3B2151` |
| **Elumichai** | lemon | `#E4C14A` |
| **Vadamalli** | bachelor's button / globe amaranth | `#8E3A7A` |
| **Kathiripoo** | brinjal flower | `#6B4A8C` |
| **Ennai arakku** | shot violet-and-brown | `#4A2E33` |
| **Elakkai** | cardamom | `#A8B08A` |
| **Pon vandu** | golden beetle | `#A8791F` |
| **Aanandha** | "bliss" blue | `#2B4C8C` |
| Zari (gold thread) | — | `#B8912F` |

**On shot colours (*manthulir*, *ennai arakku*):** these are not single colours — warp and weft are different hues and the fabric shifts as it moves. **[SOURCED]** In CSS this is a two-stop gradient that changes with viewport or hover, or a `background-blend-mode` of two flat hues. It is a genuinely distinctive effect and almost nobody uses it.

**Design read:** deep green + red is the most-attested Kanchipuram pairing and it is *already* the Vanigam palette in disguise (`#1d3d33` bottle green + an arakku red). Adding `#7B1E28` as the single accent colour would be both authentic and minimal.

### How they could serve a UI

- **Borders — this is the headline use.** Korvai gives you a *principle*: contrast-coloured, structurally-integral edges. A 4–6 px hard-edged left border in `arakku` on a bottle-green card, with no transition, is korvai.
- **The 1:6 border ratio** as the standard rule for accent-edge width relative to content width.
- **Section dividers** — the temple/muggu triangle border, single or double row, 12–16 px.
- **Top-of-section ornament** — the kalamkari thoranam festoon, 24–32 px deep, at 12% ink.
- **Empty states** — a thoranam hung over an empty field.
- **Colour system naming** — name your semantic tokens in Tamil after these colours (`--arakku`, `--mayilkazhuthu`, `--manthulir`). This is low-cost, culturally accurate, and immediately distinguishes the codebase.
- **Sparse accent rule** — the butta convention (5–8× spacing) is a direct instruction on ornament density: *the ground is mostly empty.*
- **Three-colour discipline** — Karuppur kalamkari's black/red/yellow is a sourced argument for a very small palette. Use it to resist scope creep in the colour system.

---

## Cross-cutting synthesis

Four principles recur across every tradition here, and they should drive the system more than any individual motif:

1. **Ornament lives at edges, never in the field.** Korvai borders, Athangudi border courses, hara parapets, thoranam festoons, Tanjore frames, ther panel mouldings. The field is plain — plain silk body, plain courtyard, flat painting ground. *Put decoration on boundaries; leave content areas empty.*
2. **Repetition with diminution.** Diminishing courtyards (`r ≈ 0.8`), diminishing talas (`r ≈ 0.93`), diminishing ther tiers (`r ≈ 0.85`). *Nesting scales down by a constant ratio.*
3. **Hard colour boundaries, no gradients.** Korvai is physically interlocked. Athangudi pours are discrete. Tanjore grounds are flat. *Avoid gradients except for the two authentic exceptions: shot silk, and egg-plaster satin sheen.*
4. **Restricted palettes.** Three colours for Karuppur kalamkari; 3–4 oxide pours per Athangudi tile; monochrome kolam. *Every surface: two chromatic colours maximum, plus ground and ink.*

---

## TOP 5 FOR IMPLEMENTATION

Ranked for a **restrained, premium, editorial** web UI. Criteria: reproducible geometry, low kitsch risk, palette compatibility with `#f4f1ea`/`#14120f`/`#1d3d33`/`#9a7b45`, and whether the motif does structural work rather than decorative work.

### 1. Athangudi rhombille (3D cube) as background texture
**Why it wins.** It is the only motif here that is *simultaneously* a fully specified tiling (p3 symmetry, exact lattice vectors, `<pattern>`-ready), a genuine Tamil Nadu craft form, and inherently non-figurative. Its native palette — oxide red, mustard, tile green, cement grey on lime white — is already within a few degrees of the Vanigam ground, so it costs nothing to adopt. At 8–12% ink it reads as *paper with a memory of a floor*, which is precisely the editorial-print register the product already occupies. Zero kitsch risk: at low contrast it is indistinguishable from a well-considered geometric texture, and at high contrast it is a legitimate tumbling-blocks pattern. It also scales down to a favicon and up to a full-bleed hero without changing character.
**Ship:** an SVG `<pattern>` at `41.569 × 36` px, three ink tints at 6/9/12% opacity.

### 2. Kolam single-knot line for loading, empty and progress states
**Why it wins.** Nothing else in this document has such an exact match between form and product meaning: *one continuous line, no loose ends, complete only when every point is enclosed.* For a platform whose job is to connect scattered founders into a single system, this is not decoration — it is the thesis, drawn. It is also the best-documented geometry here: two independently cited generative systems (the `{a,b,c,d}` angle-lattice method and the `FBFBFBFB` L-system), both directly implementable, both producing an Eulerian single path that animates perfectly with `stroke-dashoffset`. It is monochrome, so it can never clash. And the empty-state metaphor — a bare dot grid that resolves into a knot as the user creates things — is a product idea, not just a graphic.
**Ship:** 8–12 pre-rendered curated paths; one 1px stroke; `stroke-dashoffset` animation; a dot-grid-only variant for empty states.

### 3. Korvai border as the accent-edge principle
**Why it wins.** This is the cheapest change with the highest authenticity return. Korvai is not a pattern to draw — it is a *rule*: the border is a structurally separate, hard-contrast element interlocked with the body, never a decoration applied on top. Implementing it costs one border declaration. The sourced 1:6 border-to-body ratio gives you a defensible number for accent widths. The classic red-and-green pairing is already your palette. And the sourced Tamil colour vocabulary (arakku, mayilkazhuthu, manthulir…) gives the entire token system real names at no design cost. The shot-colour idea (manthulir, ennai arakku) is a bonus: an authentic, almost-unused gradient behaviour for hover states.
**Ship:** `--arakku: #7B1E28` as the single accent; hard 4–6px contrast edges; Tamil-named colour tokens.

### 4. Hara parapet rhythm (kuta–panjara–sala–panjara–kuta) as the divider
**Why it wins.** Editorial layouts need dividers, and a plain rule is a wasted opportunity. The hara gives a symmetric A-B-C-B-A silhouette band that is unmistakably South Indian *without a single figure or deity* — which is exactly the constraint you set. It is drawn in stone values only (greys and lime white), so it never becomes gaudy. It is fully parametrised above as fractions of the run length, so it is responsive by construction. And the tala principle behind it — each level a smaller complete repetition of the one below — is a real information-hierarchy idea you can apply to nested content at `r = 0.93`.
**Ship:** one 24px-tall SVG divider at 15% ink, parametrised by run width; plus the `r = 0.93` nesting ratio.

### 5. Tanjore gesso-and-gold frame, reserved for achievement states
**Why it wins — and why it's ranked fifth.** This is the highest-impact and highest-risk item. A shallow raised frame in 22ct-gold values around a flat, deeply saturated ground is genuinely premium and genuinely Thanjavur. But its failure mode is severe: gold used broadly reads as a wedding invitation and would destroy the editorial restraint of the whole system. So it earns a place only under a hard constraint — **reserved for milestone and verification states, with gold coverage under 5% of any surface.** Used that way it is powerful precisely because it is rare, which mirrors how gold leaf actually functions in a Tanjore painting: a small area of brilliance against a large flat ground. The prabhavali arch also gives you an unusually good empty state — an empty frame, ready.
**Ship:** one `box-shadow` gesso recipe + `#B8912F` frame; gated to milestone components only.

### Deliberately not in the top 5

- **Coimbatore Town Hall / Central Library** — the Town Hall is generic colonial neoclassical, present in every Indian district capital, and carries no distinctive Tamil visual DNA. The Central Library is architecturally undocumented in every source I could reach. Neither should carry brand weight.
- **Temple car (ther) panel grid** — an excellent card system in principle, but it overlaps heavily with what a conventional card grid already does, so it adds provenance without adding form. Worth adopting as a *justification* for the card system rather than as a new visual.
- **Chettinad plan sequence (mugappu → valavu → kattu → thottam)** — not a motif, so it can't rank as one, but it is arguably the most valuable idea in this document. Use it as the **page information architecture and vertical rhythm** (`r = 0.8`), and as naming for major layout regions. It costs nothing and it makes the structure Tamil rather than the surface.

---

## Sources

**Athangudi tiles**
- [Athangudi Tiles in Tamil Nadu's Chettinad Mansions — Paper Planes](https://www.joinpaperplanes.com/athangudi-tiles-in-tamil-nadus-chettinad-mansions/)
- [Chettiar Crafts: Athangudi Tiles — Google Arts & Culture / Dastkari Haat Samiti](https://artsandculture.google.com/story/chettiar-crafts-athangudi-tiles-dastkari-haat-samiti/2QWRMoHx4BQNJg?hl=en)
- [The Process of Making Athangudi Tiles — YirehMex](https://www.yirehmex.com/post/the-process-of-making-athangudi-tiles)
- [Athangudi Tiles: The Timeless Charm of Chettinad Craftsmanship — Futures Tiles](https://futurestilesonline.com/athangudi-tiles-the-timeless-charm-of-chettinad-craftsmanship/)
- [Chettinad Tiles — Manufacturing Process](https://chettinadtiles.com/manufacturing-process.html)
- [The Indigenous Craft of Athangudi Tiles — MeMeraki](https://www.memeraki.com/blogs/posts/the-indigenous-craft-of-athangudi-tiles)

**Chettinad architecture**
- [The Design features of Chettinad house — Rethinking The Future](https://www.re-thinkingthefuture.com/sustainable-architecture/a9906-the-design-features-of-chettinad-house/) *(403 on fetch; details drawn from search snippets)*
- [Ideas That Inspire: 6 Chettinad Elements From Heritage Mansions — Houzz](https://www.houzz.in/magazine/ideas-that-inspire-6-chettinad-elements-from-heritage-mansions-stsetivw-vs~93704669)
- [The Resplendent Mansions of India's Chettinad — Fodor's](https://www.fodors.com/world/asia/india/experiences/news/photos/mansions-of-indias-chettinad)
- [Chettinad Style House Design — UltraTech Cement](https://www.ultratechcement.com/for-homebuilders/home-building-explained-single/descriptive-articles/chettinad-style-house-design)
- [Chettinad House Architecture Design — Brick&Bolt](https://www.bricknbolt.com/blogs-and-articles/home-design-guide/chettinad-house-architecture-design)

**Kolam**
- [Symmetry Classification and Enumeration of Square-Tile Sikku Kolams — arXiv:2304.14134](https://arxiv.org/abs/2304.14134)
- [Kolam Simulation using Angles at Lattice Points — arXiv:2307.02144](https://arxiv.org/pdf/2307.02144)
- [A topological approach to creating any pulli kolam — arXiv:1503.02130](https://arxiv.org/pdf/1503.02130)
- [MathLapse: L-System for Single Knot Kolam Pattern Generation — IMAGINARY](https://www.imaginary.org/film/mathlapse-l-system-for-single-knot-kolam-pattern-generation)
- [Bluebird Math Circle Issue 45: Kolam and Circuits](https://aimathcircles.org/wp-content/uploads/2023/02/Bluebird-Newsletter-Issue-45_Kolam-and-Circuits.pdf)
- [Kolams, Code, Cultures — Algorithmic Pattern 2025](https://2025.algorithmicpattern.org/proceedings/S9NXAC/paper.html)

**Coimbatore**
- [Victoria Town Hall, Coimbatore — Wikipedia](https://en.wikipedia.org/wiki/Victoria_Town_Hall,_Coimbatore)
- [Coimbatore Town Hall Clock Tower — Indian Columbus Heritage](https://www.indiancolumbusheritage.com/2026/06/coimbatore-town-hall-clock-tower.html)
- [Tamil Nadu Public Library System — Coimbatore](http://www.punlib.net/tn/tnpls/coimbatore.html)
- [The District Central Library — Coimbatore](https://tamilnadutourisminfo.com/the-district-central-library-coimbatore/)

**Temple architecture**
- [Tala (Hindu architecture) — Wikipedia](https://en.wikipedia.org/wiki/Tala_(Hindu_architecture))
- [Temple Architecture – Devalaya Vastu (measures and proportions) — sreenivasarao's blogs](https://sreenivasaraos.com/tag/measures-and-proportions-in-temple/)
- [The Temple Towers — Madurai Meenakshi Amman Temple (official)](https://www.maduraimeenakshi.org/the-temple-towers.html)
- [Adam Hardy, *Indian Temple Architecture: Form and Transformation*](https://books.google.com/books/about/Indian_Temple_Architecture.html?id=aU0hCAS2-08C)
- [Drāviḍa Temples in the Samarāṅgaṇasūtradhāra — Adam Hardy (Cardiff University, PDF)](https://www.cardiff.ac.uk/__data/assets/pdf_file/0006/1344345/Dravida-Temples-in-the-Samaranganasutradhara-by-Adam-Hardy.pdf)
- [Built to Last: The Enduring Legacy of Pallava Art and Architecture — Asia Research News](https://www.asiaresearchnews.com/content/built-last-enduring-legacy-pallava-art-and-architecture-0)
- [Group of Monuments at Mahabalipuram — UNESCO World Heritage Centre](https://whc.unesco.org/en/list/249/)

**Temple car & Tanjore painting**
- [Temple car — Wikipedia](https://en.wikipedia.org/wiki/Temple_car)
- [Vahanam / Temple Chariots for Deities of Tamil Nadu — Asia InCH](https://asiainch.org/craft/vahanamtemple-chariots-of-tamil-nadu/)
- [Tiruvarur Chariot Festival](https://grokipedia.com/page/Tiruvarur_Chariot_festival)
- [How are Tanjore paintings made — Exotic India Art](https://www.exoticindiaart.com/blog/how-are-tanjore-paintings-made/)
- [Gold foil in Thanjavur paintings — Ethnic Tanjore Arts](https://www.ethnictanjorearts.com/is-real-gold-used-in-tanjore-painting/)
- [Tanjore Painting: The Gilded Icons of South India — Truly Bharat](https://www.trulybharat.com/culture/art-forms/tanjore-painting/)

**Kalamkari & Kanchipuram silk**
- [GI Tag for Karuppur kalamkari paintings, Kallakurichi wood carvings — GKToday](https://www.gktoday.in/gi-tag-for-karuppur-kalamkari-paintings-kallakurichi-wood-carvings/)
- [GI Tags to Karuppur Kalamkari Paintings & Kallakurichi Wood Carvings — NextIAS](https://www.nextias.com/ca/current-affairs/13-10-2021/gi-tags-to-karuppur-kalamkari-paintings-kallakurichi-wood-carvings)
- [Karuppur Kalamkari & Kallakurichi Wood Carvings Get GI Tags — iTokri](https://itokri.com/blogs/craft-masala-by-itokri/karuppur-kalamkari-paintings-kallakurichi-wood-carvings-get-geographical-indication-gi-tags)
- [The Process of Kalamkari Explained — MeMeraki](https://www.memeraki.com/blogs/posts/the-process-of-kalamkari-explained)
- [Natural Dyes of India: Plant Colours & Traditional Methods — Daughters of India](https://asia.daughtersofindia.net/pages/natural-dyes-of-india)
- [The Complete Anatomy of a Kanchipuram Silk Saree — Sampradaya Designer Studio](https://www.sampradayadesignerstudio.com/blogs/news/anatomy-of-kanchipuram-silk-saree)
- [What makes Kanchipuram korvai silk sarees so special — RMKV](https://rmkv.com/blogs/posts/what-makes-kanchipuram-korvai-silk-sarees-so-special)
- [All About Korvai Kanjivaram Silk Sarees — Singhania's](https://www.singhanias.in/blogs/singhanias-saree-journal/all-you-need-to-know-about-korvai-kanjivaram-silk-sarees)
- [5 Traditional Tamil Colour Names That Make Kanjivaram Sarees Unique — Hayagriva's Silk House](https://hayagrivassilkhouse.com/blogs/news/5-traditional-tamil-colour-names-that-make-kanjivaram-sarees-truly-unique)
- [Decoding the love for Kanjeevaram — India1001](https://www.india1001.com/blogs/1001_crafts/decoding-the-love-for-kanjeevaram)
- [The colours of Kanchipuram — RMKV](https://rmkv.com/blogs/posts/the-colours-of-kanchipuram)
- [Kanchipuram Silk Sarees: The Ultimate Guide — Fibre2Fashion](https://www.fibre2fashion.com/industry-article/10481/kanchipuram-silk-sarees-the-ultimate-guide-to-history-styling-motifs-buying-guide)
