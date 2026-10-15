# Monuments of Southern & Western Tamil Nadu — Silhouette Geometry Spec

**Purpose:** hand-authored inline SVG paths for a scroll-driven parallax panorama. No photographs, no raster. Every figure below is tagged:

- `[SOURCED]` — found in a published source, cited at the bottom.
- `[DERIVED]` — arithmetic performed here on two or more `[SOURCED]` numbers. Reliable as geometry.
- `[ESTIMATED]` — my judgement from architectural convention. **Not measured. Treat as a drawing convenience, not a fact.**
- `[UNKNOWN]` — I could not find it. Stated as a gap rather than invented.

---

## 0. Drawing conventions used throughout

To keep every monument comparable, all tier tables are normalised: **base width = 100 units**. Height figures are given both in real metres and as a ratio to base width, so you can pick any viewBox.

**Two structural grammars appear in this list, and they are opposites:**

| | Vimana (Thanjavur) | Gopuram (Madurai, Srirangam, Rameswaram) |
|---|---|---|
| Plan | square | rectangle, long axis across the gate |
| Silhouette edge | **straight** — a true pyramid | **concave** — curves inward, then flares at the top cornice |
| Taper per tier | steep, ~0.90 | shallow, ~0.96 on the wide face |
| Crown | one octagonal dome + single finial | barrel-vaulted *sala* roof + a **row** of pot finials |
| Sits over | the sanctum (the god) | the gate (the wall) |

If you draw a gopuram with straight sides it will read as a vimana and the Thanjavur/Madurai contrast — the single most important idea in this panorama — collapses. **Gopuram sides must be concave.**

---

## 1. THANJAVUR — Brihadeeswarar Temple (Big Temple)

**Caption:** *"rice bowl, agri-processing"*
**Layer depth:** **MID-GROUND** — this is the hero mass. Nothing should sit behind it; the Cauvery delta is flat, so its horizon is empty.

### Silhouette description
A single, unbroken, straight-sided pyramid rising from a near-cubic block, terminating in one octagonal dome and one spike. There is no lateral clutter — no flanking towers, no ridge of finials. Because the delta around it is dead flat and the temple's own gateways are less than half its height, it reads as a lone triangle on an empty line. At 5% opacity and 40px tall, this is still unambiguously a pyramid.

### Distinguishing feature
**The tower over the god is taller than the tower over the gate.** Everywhere else in Tamil Nadu the gopuram dwarfs the vimana. Here the main entrance gopuram is ~30 m `[SOURCED]` against a 63–66 m vimana `[SOURCED]` — **the gate is 0.45–0.47 the height of the sanctum tower** `[DERIVED]`. When you compose the Thanjavur frame, deliberately place a short, squat gopuram in front of the tall pyramid. That inversion *is* the monument.

### ⚠️ Height conflict — flagged, not resolved
| Figure | Source type |
|---|---|
| **63.4 m (208 ft)** | Wikipedia `[SOURCED]` |
| **66 m (216 ft)** | multiple secondary/tourism sources, and the figure in the project brief `[SOURCED]` |

These are not a rounding difference (208 ft vs 216 ft). Likely one measures to the top of the *sikhara* dome and the other to the tip of the *stupi* finial — the finial is 3.81 m `[SOURCED]`, which closes most but not all of the gap. **Recommendation: draw to 66 m** — it matches the brief and the common citation — but do not present the number as settled anywhere user-facing.

### Proportions

| Quantity | Value | Tag |
|---|---|---|
| Base square, side | **30.18 m (99.0 ft)** | `[SOURCED]` |
| Total height | 63.4 m *or* 66 m — see conflict | `[SOURCED]` |
| **Height : base width** | **2.10 : 1** (at 63.4 m) — **2.19 : 1** (at 66 m) | `[DERIVED]` |
| Total storeys | **16**, of which **13 are the tapering squares** | `[SOURCED]` |
| Capstone (single granite block), side | **7.77 m (25.5 ft)**, 80 tons | `[SOURCED]` |
| Sikhara dome weight | 25 tons | `[SOURCED]` |
| Stupi (finial) height | **3.81 m (12.5 ft)** | `[SOURCED]` |
| Base courtyard | 240.79 m E–W × 121.92 m N–S | `[SOURCED]` |

### Taper — the number to draw with
Capstone side ÷ base side = 7.77 / 30.18 = **0.2574**, distributed over **13 tiers**:

> **per-tier width factor = 0.2574^(1/13) = 0.90** `[DERIVED]`

**Each tier is ~0.90 the width of the one below.** Normalised tier widths (base = 100):

```
t1  100.0    t6   59.0    t11  34.9
t2   90.0    t7   53.1    t12  31.4
t3   81.0    t8   47.8    t13  28.2
t4   72.9    t9   43.0    cap  25.7  ← matches sourced 7.77/30.18 ✓
t5   65.6    t10  38.7
```

This is a genuinely self-consistent result: a 0.90 geometric taper over 13 tiers lands exactly on the measured capstone. Draw with confidence.

### Vertical division `[ESTIMATED]`
Not sourced. My estimate for a 1000-unit-tall drawing:
- 0 → 250: the two-storey cubic sanctum wall (**vertical sides, no taper**)
- 250 → 800: the 13-tier pyramid (straight hypotenuse)
- 800 → 880: octagonal *griva* (neck) — a short vertical pinch
- 880 → 940: the domed capstone (a low, wide, slightly flattened dome — **not** a hemisphere)
- 940 → 1000: the stupi finial (thin spike with 2–3 bulges)

The finial is 3.81/66 = **5.8%** of total height `[DERIVED]` — resist drawing it taller.

---

## 2. MADURAI — Meenakshi Amman Temple

**Caption:** *"temple trade, healthcare hub"*
**Layer depth:** **MID-GROUND** (the four towers) + **FOREGROUND** (one tower cropped hard at frame edge, to sell scale).

### Silhouette description
Four near-identical concave-sided towers standing at compass points around an invisible enclosure, each stepping inward through nine tiers to a horizontal barrel-vaulted cap crowned by a *row* of pot finials. The individual outline is a tall, narrow, waisted trapezoid — noticeably slimmer than Srirangam's — and the profile bows inward at mid-height before the top cornice flares out again. Read as a group they form a rhythmic picket of four verticals with the enclosure roofline running low between them.

### Distinguishing feature
**The four-tower cluster, not any single tower.** No individual Meenakshi gopuram is silhouette-distinguishable from Srirangam's or Rameswaram's — see §9. What identifies Madurai is *four of them at once*, spaced around a square, all roughly the same height (within 6% of each other, see table), so the skyline is a symmetrical four-beat rhythm rather than one dominant spike.

### ⚠️ Height conflicts — three separate contradictions, all flagged

**Conflict A — the south gopuram.** Published values:

| Value | Metric | Source |
|---|---|---|
| 170 ft | 51.8 m | Wikipedia `[SOURCED]` |
| 51.9 m | 170.3 ft | multiple sources `[SOURCED]` |
| **160.9 ft** | **49.0 m** | Tamil Nadu tourism listing `[SOURCED]` |
| 55 m | 180 ft | one secondary source `[SOURCED]` |

170 ft and 51.9 m are the *same* figure. The real disagreement is **49.0 m vs 51.9 m (a 6% spread)**, with an outlier at 55 m. **Not resolved.**

**Conflict B — internal contradiction in the tourism listing.** That same source gives the **Chittirai gopuram, 7 tiers, at 177 ft** — taller than every one of the nine-tier rajagopurams it also lists (152–161 ft). A seven-tier tower exceeding all four nine-tier towers is architecturally implausible. Either the 177 ft is wrong, or the four rajagopuram figures are. **Do not use 177 ft.**

**Conflict C — the gopuram count.** Wikipedia gives **14 gopurams**, then breaks them down as *4 nine-storey + 1 seven-storey + 5 five-storey + 2 three-storey* = **12**, plus "two gold-gilded sanctum towers" `[SOURCED]`. The count of 14 only works if the two golden vimanas are included as gopurams, which they are not. **Draw 12 gopurams + 2 golden vimanas.**

### The four outer towers — use these, with the caveat above

| Tower | Height | Base (L × W) | H : base-L | Tiers |
|---|---|---|---|---|
| **South** | 160.9 ft / 49.0 m `[SOURCED]` (disputed) | 108 × 67 ft | **1.49 : 1** `[DERIVED]` | 9 |
| **West** | 154.6 ft / 47.1 m `[SOURCED]` | 101 × 63.6 ft | **1.53 : 1** `[DERIVED]` | 9 |
| **East** | 153.3 ft / 46.7 m `[SOURCED]` | 111.3 × 65.6 ft | **1.38 : 1** `[DERIVED]` | 9 |
| **North** | 152.0 ft / 46.3 m `[SOURCED]` | 111.6 × 66.6 ft | **1.36 : 1** `[DERIVED]` | 9 |

**Drawing rule:** all four are between **1.36 : 1 and 1.53 : 1** height-to-base-width. Use **1.45 : 1** as the house value and vary ±5% per tower so the skyline isn't mechanical. Height spread across the four is only **152 → 161 ft (6%)** — keep them visibly near-equal.

Base depth-to-width is consistently ~**0.60** (e.g. 65.6/111.3) `[DERIVED]` — gopurams are wide slabs, not square. Draw the *long* face.

### Taper — 9 tiers
No published top-width for Meenakshi. Borrowing the measured Srirangam taper (§3, the only gopuram in this list with sourced base *and* top dimensions):

> **per-tier factor ≈ 0.96 on the wide face** `[ESTIMATED by analogy — Srirangam-derived]`

Normalised (base = 100): `100 · 96 · 92 · 88 · 85 · 82 · 78 · 75 · 72`. Top ≈ **0.69 × base**.

**Critically: the edge is a concave curve, not a straight line between those points.** Draw each tier's outer corner slightly inside the straight base-to-top chord — maximum inward deviation of ~**4% of base width at mid-height** `[ESTIMATED]` — then flare back out at the topmost cornice.

### Crown
Barrel-vaulted *sala* roof, long axis horizontal, sitting proud of the top tier by ~**1.15× the top width** `[ESTIMATED]`. A row of pot *kalasams* along the ridge. Count `[UNKNOWN]` for Meenakshi specifically — Srirangam's has 13 `[SOURCED]`; use an odd count of **9–13** `[ESTIMATED]`. The row of finials is the single most gopuram-identifying mark at small scale — do not omit it even at low resolution.

### Complex
Main courtyard 240 m per side, one side ~15 m longer; 14 acres (5.7 ha); golden lotus pond 50 × 37 m; hall of "1000" pillars actually has **985** `[SOURCED]`.

---

## 3. TRICHY (Tiruchirappalli) — Rockfort + Srirangam

**Caption:** *"BHEL, engineering, education"*
**Layer depth:** Rockfort = **FAR BACKGROUND / HORIZON** (it is a landform). Srirangam Rajagopuram = **MID-GROUND**. These two in one frame give Trichy instant depth — the only city here that supplies its own background and midground.

### 3a. Rockfort — Ucchi Pillayar temple

**Silhouette description.** An abrupt, asymmetric dome of bare granite erupting from an otherwise flat river plain — steep on one flank, a longer shallow shoulder on the other. A thin pale zigzag of covered steps climbs the flank. At the crest, off-centre, sits one very small white shrine with a squat pyramidal cap. The whole reads as a rounded mass with a single tiny nick at the top.

**Distinguishing feature.** **The scale mismatch.** The rock is 83 m `[SOURCED]`; the shrine on it is tiny. The temple is roughly **0.10–0.12 of the rock's height** `[ESTIMATED]` — draw it almost too small. If the shrine looks like a proper temple, you have drawn a hill with a temple on it; the actual Rockfort is a *rock that happens to have a dot on top*. That dot, off-centre, is the identifier.

| Quantity | Value | Tag |
|---|---|---|
| Height above surrounding plain | **83 m (272 ft)** | `[SOURCED]` |
| Summit elevation | **126.17 m (414 ft) ASL** | `[SOURCED]` |
| **Plain-to-rock silhouette ratio** | rock is 83 m against a horizon at 0 | `[SOURCED]` |
| Base width of the outcrop | `[UNKNOWN]` — no published figure found | — |
| Number of steps to summit | `[UNKNOWN]` — "437" is widely repeated online but I could not verify it in a reliable source. **Do not cite it.** | — |
| Geological age | `[UNKNOWN]` — "3.8 billion years, among the oldest rocks on Earth" is widely repeated and **unverified**. Do not put it in copy. | — |

**Drawing profile `[ESTIMATED]`:** width:height ≈ **2.2 : 1** for the outcrop. Steep face ~55–65° from horizontal; opposite shoulder ~25–30°. Crown the summit at ~60% along the width, not at 50% — the asymmetry is what stops it reading as a generic hill.

### 3b. Srirangam — Rajagopuram (tallest gopuram in Asia)

**Silhouette description.** The same concave-sided, tiered, barrel-capped gopuram grammar as Madurai, but **substantially fatter and taller** — 13 tiers instead of 9, and a base half again as wide. Where a Meenakshi tower is a narrow blade, this is a broad wedge. Thirteen large pot finials line its top ridge.

**Distinguishing feature.** **Bulk, and the row of 13 finials.** Its base long-side is **50.6 m** `[SOURCED]` — wider than the entire Thanjavur vimana's 30.18 m base. Also uniquely: the temple's main vimana is gilded and **shaped like the Tamil *omkara* (ॐ / ஓம்) symbol** `[SOURCED]` — a curved, non-pyramidal gold form. If you can afford one extra shape in the Trichy frame, make it that: nothing else in South India has a curved golden vimana.

| Quantity | Value | Tag |
|---|---|---|
| Height | **73 m (240 ft)** (completed 1987) | `[SOURCED]` |
| Tiers | **13** | `[SOURCED]` |
| Base | **50.6 × 29.6 m** | `[SOURCED]` |
| Top | **29.9 × 9.8 m** | `[SOURCED]` |
| **Height : base width** | **1.44 : 1** | `[DERIVED]` |
| Base depth : width | 29.6/50.6 = **0.585** | `[DERIVED]` |
| Kalasams (copper finials) | **13**, each **3.12 m** high, 135 kg | `[SOURCED]` |
| Vellai gopuram (secondary) | ~44 m (144 ft) | `[SOURCED]` |
| Complex | 63 ha (155 acres), 7 concentric prakarams, outer wall 9,934 m | `[SOURCED]` |

### ★ The measured taper — the most valuable number in this document

Srirangam is the only tower here with **both** base and top dimensions published, so it calibrates every other gopuram in the panorama:

- Wide face: 29.9 / 50.6 = **0.591** over 13 tiers → **per-tier factor = 0.9603** `[DERIVED]`
- Depth: 9.8 / 29.6 = **0.331** over 13 tiers → **per-tier factor = 0.9187** `[DERIVED]`

**A gopuram tapers much harder in depth than in width.** For a front-elevation silhouette use **0.96 per tier**. Normalised (base = 100):

```
t1 100 · t2 96 · t3 92 · t4 89 · t5 85 · t6 82 · t7 78
t8 75 · t9 72 · t10 69 · t11 66 · t12 64 · t13 61 → cap 59
```

Finial height as a fraction of total: 3.12 / 73 = **4.3%** `[DERIVED]`.

---

## 4. RAMESWARAM — Ramanathaswamy Temple + Pamban Bridge

**Caption:** *"fisheries, pilgrimage tourism"*
**Layer depth:** Pamban bridge = **MID-GROUND** (spanning the full frame width, on water). Corridor colonnade = **FOREGROUND** (columns entering from frame edge, receding). Gopuram = **MID-GROUND** behind the bridge. This is the richest three-layer city in the set.

### 4a. The corridor — the world's longest temple corridor

**Silhouette description.** Not a tower at all: a purely horizontal element. A long receding colonnade of tall, closely spaced rectangular piers under a flat continuous lintel, with a dark band of roof above and a raised plinth below. In silhouette it is a **barcode** — a rhythm of verticals of identical height, converging with perspective, capped top and bottom by two horizontal lines.

**Distinguishing feature.** **Length, expressed as rhythm.** No other monument here is a repeat-unit. Use it as a foreground parallax layer that scrolls fastest — a picket of columns sliding past the camera. The columns should be *tall relative to their spacing* (roughly 3:1) so the gaps stay narrow and the rhythm reads as dense, not airy.

| Quantity | Value | Tag |
|---|---|---|
| Outer (third) corridor, total length | **3,850 ft (~1,173 m)** | `[SOURCED]` |
| — east and west sections | 400 ft each | `[SOURCED]` |
| — north and south sections | ~640 ft each | `[SOURCED]` |
| Corridor width | **15.5–17 ft** (E/W), 14.5–17 ft (N/S) | `[SOURCED]` |
| Corridor height | **~6.9 m** | `[SOURCED]` |
| Pillars, outer corridor | **~1,212** | `[SOURCED]` |
| Pillar height, floor to centre of roof | **~30 ft (9.1 m)** | `[SOURCED]` |
| Inner corridor | 224 ft (E/W), 352 ft (N/S) | `[SOURCED]` |
| Main gopuram | **53 m** | `[SOURCED]` |
| Compound wall | ~865 ft E–W × 657 ft N–S | `[SOURCED]` |

### ⚠️ Arithmetic conflicts in the sourced corridor figures
1. **Section lengths don't sum to the total.** 2×400 + 2×640 = **2,080 ft**, but the total is given as **3,850 ft**. The 3,850 may count both parallel rows, or a different corridor. Unreconciled.
2. **Corridor height 6.9 m vs pillar height 9.1 m.** A 9.1 m pillar cannot stand in a 6.9 m corridor. These are almost certainly measured to different datums (one to the eave, one to the roof-vault centre), but as published they contradict.

**Consequence for drawing:** the pillar *count* and *spacing* cannot be derived reliably from these numbers. Do not compute one.

**Use this instead `[ESTIMATED]`:** column height : centre-to-centre spacing = **3 : 1**; column width : height = **1 : 9**; plinth height = 0.12 × column height; lintel + roof band = 0.20 × column height above the capital. Draw 20–40 bays across the viewport and let it tile.

### 4b. Pamban Bridge — the horizon line

**Silhouette description.** A dead-flat horizontal deck line held above the sea on a long series of short, evenly spaced piers, interrupted exactly once near mid-span. The old bridge's interruption is a **V** — two bascule leaves rising apart. The new bridge's interruption is a **rectangular portal** — two towers and a crossbeam, a goalpost. Everything else is pure repetition.

**Distinguishing feature.** **The single interruption in an otherwise perfectly regular rhythm.** This is the most legible shape in the entire panorama at tiny sizes (see §9). Choose one era and commit — the V (historic, romantic) or the goalpost (current, since April 2025). Drawing both in one frame is factually wrong at any single date and visually muddles the read.

**Old bridge (1914–2022)** `[SOURCED]`

| Quantity | Value |
|---|---|
| Total length | **2,065 m (6,775 ft)** |
| Spans / piers | **144 spans, 143 piers** |
| Deck height above sea level | **12.5 m (41 ft)** |
| Lift span | Scherzer double-leaf rolling bascule, **65.23 m (214 ft)** |
| Leaf weight | 415 t each; manual operation 45 min per cycle |

**Derived rhythm — use these** `[DERIVED]`
- Pier spacing = 2,065 / 143 = **14.4 m**
- **Spacing : deck height = 14.4 : 12.5 = 1.15 : 1** — piers are almost as tall as they are far apart. A tight, insistent rhythm, not a lazy one.
- Lift span = 65.23 m ≈ **4.5 normal bays** — the gap in the rhythm is noticeably wider than the others. Draw it that way.
- Total length : deck height = 2,065 : 12.5 = **165 : 1**. Extremely flat. It will span your whole viewport at a hairline thickness — that is correct.

**New bridge (opened April 2025)** `[SOURCED]`

| Quantity | Value |
|---|---|
| Length | **2.08 km** |
| Spans | **99** |
| Vertical lift span | **72.5 m**, lifts to **17 m** |
| Navigational air clearance | **22 m** above sea level |
| Height vs old bridge | **3 m higher** |
| Cost / rating | ₹550 cr; rated 80 km/h, 100-year design life |

**Derived** `[DERIVED]`: pier spacing = 2,080 / 99 ≈ **21 m** — a *slower, wider* rhythm than the old bridge. Deck ~15.5 m ASL (12.5 + 3). Lift span = 72.5 m ≈ **3.5 bays**. The two lift towers rise to ≥22 m — about **1.4× deck height** above sea level, so the goalpost sticks up clearly above the deck line.

---

## 5. KANYAKUMARI — Vivekananda Rock Memorial + Thiruvalluvar Statue

**Caption:** *"wind energy, coastal tourism"*
**Layer depth:** Both = **MID-GROUND**, sitting on an empty **FAR BACKGROUND** (open sea horizon, no land). Optionally a **FOREGROUND** of low rocks/surf line.

### Silhouette description
Two separate rocks in open water, ~500 m offshore `[SOURCED]`, carrying two shapes that could not be more different: on one, a low wide flat-roofed hall with a single stepped tower rising over one end; on the other, a lone standing human figure on a tall plinth. Between them, a clean gap of empty sea. Behind them, nothing — this is the tip of the subcontinent, so the horizon is uninterrupted.

### Distinguishing feature
**The pairing across water.** One horizontal mass + one vertical figure + a gap. No other site in Tamil Nadu presents a *human figure* in silhouette, and a standing figure is the fastest-recognised shape a human eye processes. Do not merge the two rocks into one platform — the gap of sea between them is load-bearing.

### 5a. Vivekananda Rock Memorial

| Quantity | Value | Tag |
|---|---|---|
| Distance offshore | **~500 m** | `[SOURCED]` |
| Vivekananda Mandapam footprint | **130 ft 1½ in × 56 ft** (39.6 × 17.1 m) | `[SOURCED]` |
| **Plan aspect ratio** | **2.32 : 1** | `[DERIVED]` |
| Elevation figure | **16.764 m (55.00 ft)** | `[SOURCED]` — ⚠️ **ambiguous**: the source does not state whether this is structure height or rock elevation ASL. Flagged. |
| Dome / tower height | `[UNKNOWN]` | — |

**Drawing `[ESTIMATED]`:** overall facade width : height ≈ **3 : 1**. Long low horizontal body occupying the left/lower ~70% of the mass, with one stepped, squarish tower over the sanctum at one end rising to ~1.8× the body height. Flat roofline with a light parapet. The mandapam sits on bare rock — include 0.3–0.5 body-heights of irregular rock below it, meeting the waterline.

### 5b. Thiruvalluvar Statue

| Quantity | Value | Tag |
|---|---|---|
| **Total height** | **40.6 m (133 ft)** | `[SOURCED]` |
| Sculpture (figure only) | **29 m (95 ft)** | `[SOURCED]` |
| Pedestal | **12 m (38 ft)** | `[SOURCED]` |
| **Pedestal : figure** | **38 : 95 = 1 : 2.5** | `[DERIVED]` |
| Pedestal as fraction of total | **28.6%** | `[DERIVED]` |
| Head elevation ASL | 61 m | `[SOURCED]` |
| Face height | **6 m (19 ft)** | `[SOURCED]` |
| Mass / stones | 7,000 t; 3,681 stones; largest blocks 4 m / 15 t | `[SOURCED]` |
| Posture | slight forward bend, recalling a classical dance pose | `[SOURCED]` |

**133 ft = the 133 chapters of the Thirukkural**; the 38 ft pedestal = the 38 chapters on virtue `[SOURCED]`. Good copy, and it also *justifies the proportion* — the 1:2.5 plinth ratio is symbolic, not arbitrary, so don't "improve" it.

**Drawing `[ESTIMATED]`:** face 6 m against a 29 m figure ⇒ roughly **4.8 face-heights** of body — i.e. the figure is drawn in a **heroic/compressed canon, not the 7.5-head classical human proportion**. Draw the head noticeably large relative to the body or it will read as a modern statue. Figure silhouette: draped robe flaring to a wide base (robe hem width ≈ 0.30 × figure height), narrowing at the chest, one arm held across the body. Total statue height : pedestal width ≈ **4 : 1** `[ESTIMATED]` — pedestal width is `[UNKNOWN]`.

---

## 6. COIMBATORE / OOTY — Nilgiris, the Mountain Railway, mills and turbines

**Captions:** Coimbatore — *"pumps, textiles, engineering startups"* · Ooty — *"tea, tourism, horticulture"*
**Layer depth:** Nilgiri ridge = **FAR BACKGROUND**. Mill roofline + chimneys, wind turbines = **MID-GROUND**. NMR train + tea terraces = **FOREGROUND**.

### 6a. The Nilgiri ridge profile — the one genuinely useful research finding here

**Silhouette description.** A long, low, *rounded* ridge line. Not alpine. The Nilgiris are grassland-and-shola downs — the profile is a series of shallow domes, no spires, no exposed rock teeth, no snowline.

**The numbers make this precise.** Peaks in the Doddabetta group `[SOURCED]`:

| Peak | Height |
|---|---|
| **Doddabetta** | **2,637 m** (8,652 ft) — highest in the Nilgiris |
| Kolaribetta | 2,630 m |
| Makurni | 2,594 m |
| Mukurthi | 2,554 m |
| Snowdon | 2,530 m |
| Kulkudi | 2,439 m |
| Kattadadu | 2,418 m |
| Hecuba | 2,375 m |

**Derived, and this is the drawing rule:** the entire named skyline spans **2,375 → 2,637 m — a range of just 262 m, only 10% of the peak height** `[DERIVED]`.

> **Draw the Nilgiri ridge as a gently undulating line whose peaks and troughs vary by only about 10% of its height above the plateau.** Sharp triangular mountains would be factually and visually wrong.

Ooty town sits at **2,203 m** `[SOURCED]`, so Doddabetta rises only ~434 m above the town — the "mountains" barely clear the plateau they sit on. The far layer should be a soft, near-flat wave.

### 6b. Nilgiri Mountain Railway (UNESCO)

**Silhouette description.** A short train on a thin line clinging to a hillside — a squat steam locomotive with a tall stack, pushing (not pulling) two or three small coaches, crossing a viaduct of slender arches or emerging from a tunnel mouth.

**Distinguishing feature.** **The locomotive is at the downhill end, pushing the coaches uphill** — the reverse of every other train silhouette. `[ESTIMATED — standard operating practice for the NMR rack section, widely reported, but not confirmed in the sources I fetched.]` Combine with the tunnel-mouth arch and the shallow-arched viaduct.

| Quantity | Value | Tag |
|---|---|---|
| Length | **46 km (29 mi)** | `[SOURCED]` |
| Gauge | **1,000 mm metre gauge** | `[SOURCED]` |
| **Max gradient** | **8.33% (1 in 12)** — steepest in Asia | `[SOURCED]` |
| Average gradient, rack section | 1 in 24.5 (4.08%) | `[SOURCED]` |
| Rack system | **Abt** rack-and-pinion, Mettupalayam→Coonoor | `[SOURCED]` |
| Tunnels / bridges | **16 tunnels, 250 bridges** | `[SOURCED]` |
| Mettupalayam elevation | 325.8 m (1,069 ft) | `[SOURCED]` |
| Udhagamandalam elevation | 2,203.1 m (7,228 ft) | `[SOURCED]` |
| Total climb | **1,877 m over 46 km** | `[DERIVED]` |
| Locomotive | **X-class steam rack loco**, Swiss Locomotive & Machine Works | `[SOURCED]` |
| Speed | 30 km/h level, **15 km/h climbing** | `[SOURCED]` |

### ⚠️ Honest warning about the gradient
**8.33% is only 4.8° from horizontal** `[DERIVED]`. If you draw the track at its true gradient it will look flat and the "steepest railway in Asia" idea will not land. **Exaggerate to 15–20° (a 3–4× vertical stretch) for legibility**, and know that you are stylising. Say so in a code comment.

### 6c. Coimbatore's industrial layer

`[SOURCED]`: Textile mills draw close to **3 GW** of Tamil Nadu's wind generation through captive arrangements, and **~40% of the state's wind farms are owned by the textile industry**. That is the real reason mills and turbines belong in the same silhouette — this is not a decorative pairing, it is the actual economic structure of the Kongu belt. Good caption material.

**Mill silhouette `[ESTIMATED]` — no published mill dimensions found:** a long low shed with a **north-light sawtooth roof** (a repeating right-triangle ripple, ~8–14 teeth across), one or two tall slender brick chimneys rising to **~3× the shed height**. The sawtooth is the identifier — it says "factory" faster than any other roofline.

**Wind turbine silhouette `[ESTIMATED]` — no TN-specific turbine spec found:** Tamil Nadu's older fleet is small machines. Draw tower height ≈ rotor diameter (a well-known modern-turbine convention), three blades, one blade vertical-up in most instances, and **vary the rotor phase between adjacent turbines** — identical phase reads as a pattern, varied phase reads as a wind farm. Cluster 5–9 across a ridge at diminishing scale.

---

## 7. CHETTINAD (Karaikudi) — the mansions

**Caption:** *"banking diaspora, heritage tourism"*
**Layer depth:** **FOREGROUND** — a facade the camera passes close to. Its horizontality is wasted in the distance.

### Silhouette description
The exact inverse of a gopuram: a long, low, emphatically horizontal facade, one or two storeys, sitting on a raised plinth, perfectly symmetrical about a single tall ornate central doorway. A colonnade of slender columns runs the full width. The roof is **flat**, terminated by a decorated parapet, with a small raised pediment over the central entrance. Two low raised platforms (*thinnai*) flank the door at plinth level, projecting forward and breaking the base line.

### Distinguishing feature
**A flat roof with a parapet, and bilateral symmetry about a single door.** Every temple in this panorama terminates in a curved, domed or vaulted top with finials; the Chettinad mansion terminates in a *straight horizontal line*. Placed in the same scroll as Thanjavur and Madurai it is a deliberate visual full stop. Second identifier: the parapet carries small figures set in crested frames `[SOURCED]` — a row of tiny bumps along the roofline that catches the eye at silhouette scale.

### ⚠️ Honest gap — read this before drawing
**I could not find published dimensions for any Chettinad mansion.** No facade width, no storey height, no column height, no bay spacing, no plinth height, in any source I searched. Everything numeric below is `[ESTIMATED]` from architectural convention and should be treated as a *starting point to be art-directed*, not as measured fact. This is the least-sourced monument in the document.

**What IS sourced:**
- The house is planned as a sequence of zones along an east–west axis, with all colonnades, rooms and steps in **binary symmetry** `[SOURCED]`.
- Five zones in order: **Mugappu** (entrance/reception) → **Valavu** → **Irandankattu** → **Moonamkattu** → **Thottam** `[SOURCED]`.
- **Two raised platforms (*thinnai*) flank the entrance** `[SOURCED]`.
- The Mugappu connects to the Valavu through an ornate doorway, the principal entrance `[SOURCED]`.
- Parapets on upper storeys display **deities in crested frames** `[SOURCED]`.
- Materials: Burma teak columns, Athangudi tiles, egg-plaster walls, granite, marble; oldest examples ~1870 `[SOURCED]`.

**Estimated proportions for drawing `[ESTIMATED]` — all unverified:**

| Quantity | Estimate |
|---|---|
| Facade width : height | **4 : 1** (range 3:1 to 5:1) |
| Storeys | 1–2 |
| Plinth height | 0.15 × facade height |
| Columns across the front | **8–12**, odd bay count so a bay centres on the door |
| Column height : diameter | **10 : 1** — very slender, teak |
| Column spacing : column height | **0.6 : 1** |
| Central doorway height | 0.75 × storey height, ~2.5× a bay in width |
| Parapet height | 0.08 × facade height |
| Central pediment rise | 0.12 × facade height above the parapet line |
| Thinnai platform | plinth-height, projecting ~0.5 × storey height forward |
| Plan depth | 100 m+, several sequential courtyards `[ESTIMATED from the sourced 5-zone sequence]` |

---

## 8. Parallax layer assignment (complete scene)

| Layer | Scroll speed | Contents |
|---|---|---|
| **Sky / gradient** | 0.0 | continuous across all cities; only the palette changes |
| **Far background** | 0.15 | Nilgiri ridge (±10% undulation); Trichy Rockfort; open-sea horizon at Kanyakumari; flat empty line at Thanjavur |
| **Mid-ground** | 0.45 | Thanjavur vimana; Madurai's four towers; Srirangam Rajagopuram; Pamban bridge; Vivekananda memorial + Thiruvalluvar; mills, chimneys, wind turbines |
| **Foreground** | 1.0 | Rameswaram corridor colonnade; Chettinad facade; NMR train and viaduct; palms; a cropped gopuram base at frame edge |

**Every city needs a far layer.** Thanjavur and Madurai have no natural background — supply palms, a distant haze band, or the low enclosure wall, or those frames will read as flat.

---

## 9. The three that read best at small scale and low contrast

Chosen for **silhouette legibility**, not fame.

### 1. Pamban Bridge — *the clearest by a wide margin*
A long horizontal line of evenly spaced verticals, broken exactly once. Rhythm survives destruction: at 1–2 px stroke weight and 5% opacity the eye still resolves "repeating structure with one interruption." Its aspect ratio (165:1) means it spans the full viewport without needing internal detail, and the single break gives the eye a target. **No other monument here is legible at 20 px tall. This one is.**

### 2. Thanjavur Brihadeeswarar vimana — *the clearest single mass*
A solid straight-sided triangle with one apex and no competing verticals. The steep 0.90 taper is aggressive enough that the pyramid reads as a pyramid even when the tier steps blur into a smooth edge — which is exactly what happens at small scale, and it costs nothing. Contrast this with a gopuram, whose 0.96 taper blurs into a near-*rectangle*.

### 3. Kanyakumari's pair — *the clearest composition*
Two marks with a gap: one low horizontal block, one thin vertical figure. Human silhouette recognition is the fastest visual channel available, and the empty sea horizon behind gives maximum figure-ground contrast — no other site in the set has a guaranteed-empty background. Legible as *shape relationship* rather than as detail, which is what survives low opacity.

### ⚠️ The trap: Madurai, Srirangam and Rameswaram gopurams are near-identical in silhouette
All three are concave-sided, tiered, barrel-capped towers with a finial row. Their real differences — 9 vs 13 tiers, 1.45:1 vs 1.44:1 aspect — are **invisible at panorama scale and low opacity**. If the user is meant to tell Madurai from Trichy from Rameswaram, **the tower alone will not do it.** Differentiate by *composition*, not by tower geometry:

- **Madurai** → four towers, near-equal height, symmetrically spaced. A four-beat rhythm.
- **Trichy** → one tower, plus the 83 m rock behind it. A tower against a dome.
- **Rameswaram** → one tower, plus the bridge and the foreground colonnade. A tower against a horizontal line.

---

## 10. Captions — one per city, economic association

| City | Caption |
|---|---|
| **Thanjavur** | rice bowl, agri-processing |
| **Madurai** | temple trade, healthcare hub |
| **Trichy** | BHEL, engineering, education |
| **Rameswaram** | fisheries, pilgrimage tourism |
| **Kanyakumari** | wind energy, coastal tourism |
| **Coimbatore** | pumps, textiles, engineering startups |
| **Ooty** | tea, tourism, horticulture |
| **Karaikudi (Chettinad)** | banking diaspora, heritage tourism |

*(Reference from the brief: Tiruppur — "knitwear, exports".)*

---

## 11. Summary of every gap and conflict

**Unresolved conflicts — do not present as settled fact:**
1. Thanjavur vimana height: **63.4 m vs 66 m**.
2. Meenakshi south gopuram: **49.0 m vs 51.9 m**, outlier at 55 m.
3. Meenakshi Chittirai gopuram listed at 177 ft (7 tiers) — taller than every 9-tier tower in the same source. Implausible.
4. Meenakshi gopuram count: stated 14, itemised 12.
5. Rameswaram corridor: sections sum to 2,080 ft, total given as 3,850 ft.
6. Rameswaram corridor height 6.9 m vs pillar height 9.1 m — mutually impossible as published.

**Genuine gaps — nothing invented:**
- Rockfort outcrop **base width**; **step count** (the widely-repeated "437" is unverified); **geological age** (the "3.8 billion years" claim is unverified — keep it out of copy).
- Vivekananda Memorial **dome/tower height**; the sourced 16.764 m is of ambiguous datum.
- Thiruvalluvar **pedestal width**.
- Meenakshi **kalasam count** and **top-width** (taper borrowed from Srirangam).
- **All Chettinad dimensions.** Entirely `[ESTIMATED]`.
- Coimbatore **mill and turbine dimensions.** Entirely `[ESTIMATED]`.
- NMR locomotive **push-from-downhill** operating detail — widely reported, not confirmed in sources fetched here.

**Strongest, most reliable numbers in this document** — build the scene around these:
- Thanjavur: base 30.18 m, capstone 7.77 m, 13 tiers → **taper 0.90/tier, internally consistent** `[DERIVED from two SOURCED figures]`
- Srirangam: base 50.6 × 29.6 m, top 29.9 × 9.8 m, 13 tiers → **taper 0.96/tier wide face, 0.92/tier depth** `[DERIVED from four SOURCED figures]`
- Pamban: 2,065 m / 143 piers / 12.5 m deck → **14.4 m spacing, 1.15:1 spacing-to-height** `[DERIVED]`
- Nilgiris: 8 named peaks, 2,375–2,637 m → **10% ridge undulation** `[DERIVED]`

---

## Sources

- [Brihadisvara Temple, Thanjavur — Wikipedia](https://en.wikipedia.org/wiki/Brihadisvara_Temple,_Thanjavur)
- [Temple Architecture | Brihadeeswara Temple](https://www.brihadeeswaratemple.com/architecture/)
- [Brihadishvara Temple — Britannica](https://www.britannica.com/place/Brihadishvara-temple)
- [Brihadeeswarar Temple, Thanjavur: The Chola Vimana — Studio Matrx](https://www.studiomatrx.org/architecture-canon/brihadeeswarar-temple-thanjavur)
- [Meenakshi Temple — Wikipedia](https://en.wikipedia.org/wiki/Meenakshi_Temple)
- [Meenakshi Amman Temple – Gopurams (Towers) — Tamil Nadu tourism listing](https://tamilnadu-favtourism.blogspot.com/2015/12/meenakshi-amman-temple-gopurams-towers.html)
- [Meenakshi Amman Temple — Incredible India](https://www.incredibleindia.gov.in/en/tamil-nadu/madurai/meenakshi-amman-temple)
- [Ranganathaswamy Temple, Srirangam — Wikipedia](https://en.wikipedia.org/wiki/Ranganathaswamy_Temple,_Srirangam)
- [Ucchi Pillayar Temple, Rockfort — Wikipedia](https://en.wikipedia.org/wiki/Ucchi_Pillayar_Temple,_Rockfort)
- [Ramanathaswamy Temple — Wikipedia](https://en.wikipedia.org/wiki/Ramanathaswamy_Temple)
- [Pamban Bridge — Wikipedia](https://en.wikipedia.org/wiki/Pamban_Bridge)
- [New Pamban Bridge — Wikipedia](https://en.wikipedia.org/wiki/New_Pamban_Bridge)
- [Pamban Bridge inauguration: India's first vertical lift sea bridge — Business Standard](https://www.business-standard.com/india-news/pamban-bridge-inauguration-rameswaram-india-first-vertical-lift-sea-bridge-125040600240_1.html)
- [Vivekananda Rock Memorial — Wikipedia](https://en.wikipedia.org/wiki/Vivekananda_Rock_Memorial)
- [Thiruvalluvar Statue — Wikipedia](https://en.wikipedia.org/wiki/Thiruvalluvar_Statue)
- [Nilgiri Mountain Railway — Wikipedia](https://en.wikipedia.org/wiki/Nilgiri_Mountain_Railway)
- [Doddabetta — Wikipedia](https://en.wikipedia.org/wiki/Doddabetta)
- [Nilgiri Mountains — Wikipedia](https://en.wikipedia.org/wiki/Nilgiri_Mountains)
- [Doddabetta, Ooty — Tamil Nadu Tourism](https://www.tamilnadutourism.tn.gov.in/destinations/doddabetta-ooty)
- [Energy storage, offshore wind now central to Tamil Nadu's clean power future — Down To Earth](https://www.downtoearth.org.in/energy/energy-storage-offshore-wind-now-central-to-tamil-nadus-clean-power-future)
- [Karaikudi Travel Guide: Exploring Chettinad Mansions — Outlook Traveller](https://www.outlooktraveller.com/destinations/india/the-gentle-temptations-of-karaikudi-a-town-of-grand-chettinad-mansions)
- [Chettinad Mansions: an Architecture Perspective — Memorytrain](https://memorytrain.com/blogs/news/chettinad-mansion-in-an-architecture-perspective)
- [Chettinad House Architecture Design — Brick&Bolt](https://www.bricknbolt.com/blogs-and-articles/home-design-guide/chettinad-house-architecture-design)
