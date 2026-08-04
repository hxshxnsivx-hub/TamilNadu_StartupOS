# Monuments of Northern & Central Tamil Nadu — Silhouette Geometry Spec

**Purpose.** Supply an engineer with enough *geometry and proportion* to hand-author inline SVG silhouettes of six Tamil Nadu cities, for a scroll-driven parallax background. No photographs, no raster assets, no external requests. Every shape here must be drawable from `<path>` data alone.

**Scope note.** This document deliberately ignores history, iconography and surface carving. At the target rendering size (a monument occupies roughly 120–400px of a 1440px-wide viewport) and at the target opacity (0.10–0.35 for background layers), *only the outline survives*. Everything below is about outline.

---

## CONFIDENCE LEGEND — read this before using any number

Matching the convention in `art-reference-tn.md`. Do not silently promote a tag.

- **[SOURCED]** — stated in a cited source. Safe to rely on.
- **[DERIVED]** — arithmetic on [SOURCED] numbers (e.g. a per-tier taper computed from a sourced total height and sourced tier count). Reproducible, but the endpoints I fed the arithmetic may themselves be estimates — each instance says which.
- **[ESTIMATED]** — my judgement. Not sourced. Drawable and plausible, but **not a fact about the building.** If accuracy matters for a given monument, these are the numbers to go re-measure.

### The honest gaps, stated up front

Published sources for Indian monuments reliably give **total height** and **number of storeys**. They almost never give **base width**, **top width**, or **per-tier taper** — the three numbers you actually need to draw a tapering tower. I found sourced base dimensions for exactly two structures in this set (Annamalaiyar Rajagopuram; Dharmaraja Ratha). Everything else's width is [ESTIMATED].

Specifically **not sourced anywhere I searched**:

- Base footprint of the Ekambareswarar, Kapaleeshwarar, and Jalakandeswarar gopurams
- Height of the Kailasanathar vimana at Kanchipuram, and its exact storey count (sources say "four-storey" but also "many levels")
- Height of the Shore Temple's *smaller* western vimana
- Height of the Senate House and its towers
- Individual dimensions of the Nakula-Sahadeva Ratha
- Vellore Fort wall height/thickness and moat width from a primary source (secondary sources give figures; Wikipedia does not corroborate them)
- Kalasam (finial pot) counts for any specific gopuram in this set

Where a number is [ESTIMATED] I have kept it *conservative and generic* — a plausible South Indian proportion rather than an invented precision. Drawing from these will produce a recognisable, honest silhouette; it will not produce a measured elevation.

---

## 0. DRAWING CONVENTIONS

Adopt these so all six panels compose.

### 0.1 Panel coordinate system

Each city is one panel in a horizontally-scrolling `viewBox`.

```
Panel: 1000 × 600 user units
Horizon / groundline:  y = 520
Sky:                   y = 0 … 520
Foreground apron:      y = 520 … 600
```

All monument heights below are given in **panel units (pu)**, measured up from `y = 520`. Convert with the per-city scale factor given in each section. Y increases downward in SVG, so a monument of height `H` has its apex at `y = 520 - H`.

### 0.2 The three parallax layers

| Layer | Scroll factor | Content | Fill treatment |
|---|---|---|---|
| **FAR** | 0.15–0.25× | hills, sea horizon, distant towers, city massing | flat, opacity 0.10–0.18, no internal detail |
| **MID** | 0.45–0.60× | the hero monument | opacity 0.22–0.35, may carry 1–2 internal negative-space cuts |
| **FORE** | 0.90–1.10× | gate, pillar, palm, boat, balustrade | opacity 0.55–0.85, often cropped by the panel edge |

**Rule:** every city needs all three. If a city has no natural far-background feature (Chennai, Kanchipuram — both flat), invent one from the sourced repertoire (a low massing of gopuram tops, a sea line) rather than leaving the layer empty. A missing FAR layer collapses the parallax and the scroll stops reading as travel.

### 0.3 The gopuram construction algorithm

Four of the six cities are carried by a gopuram. Write **one** parametric generator and reuse it. This is the single highest-leverage piece of code in the whole background.

A gopuram is not a smooth pyramid. It is a **rectangular granite base** carrying a **battered, storeyed superstructure**, capped by a **barrel-vaulted roof (śāla)** laid *transversely* — its long axis runs across the tower's width — and topped by a row of **pot finials (kalasam)**. [SOURCED — Wikipedia, *Gopuram*: "usually tapering oblong structures… multiple storeys (talas) that diminish in scale as they ascend… topped with a barrel-vaulted roof crowned with finials (kalasam)".]

```
GOPURAM(H, W, N):
  H = total height (pu)
  W = base width (pu)
  N = number of tiers (talas)

  # 1. BASE — vertical, no taper. This block is what makes it read
  #    as a gopuram and not a generic pyramid. Do not skip it.
  base_h = 0.20 * H            # [ESTIMATED] range 0.16–0.24
  rect(x = -W/2, y = -base_h, w = W, h = base_h)

  # 2. SUPERSTRUCTURE
  super_h = 0.74 * H           # [ESTIMATED]
  W_top   = 0.50 * W           # [ESTIMATED] range 0.45–0.55
  for i in 0 .. N-1:
      t   = i / (N - 1)
      # p > 1 bows the sides gently INWARD (concave batter).
      # p = 1.0 gives a straight-sided cone — acceptable but flatter.
      p   = 1.18               # [ESTIMATED]
      w_i = W_top + (W - W_top) * pow(1 - t, p)
      # tier heights also shrink, slightly slower than widths
      h_i = h_0 * pow(0.93, i)     # h_0 solved so sum(h_i) = super_h
      # draw tier i as a TRAPEZOID (w_i at bottom → w_{i+1} at top)
      # then add the KAPOTA LIP: a 0.030*W outward flare at the tier's
      # top edge, 0.35*h_i tall. The lip is what produces the stepped,
      # serrated silhouette edge. Without it the tower reads as a
      # smooth cone and loses all South Indian character.

  # 3. ŚĀLA (barrel-vaulted crown), drawn transversely
  sala_w = 1.15 * W_top        # [ESTIMATED] it oversails the top tier
  sala_h = 0.060 * H           # [ESTIMATED]
  # profile: vertical sides for 0.35*sala_h, then a semi-ellipse
  # (rx = sala_w/2, ry = 0.65*sala_h) over the top.

  # 4. KALASAM row along the śāla ridge
  # odd count, scaling with N: N<=7 → 5 pots; N in 8..10 → 9 pots;
  # N >= 11 → 13 pots.  [ESTIMATED — the "13 on the largest gopurams"
  # figure is widely repeated but I could not source it for any
  # specific tower in this set. Treat as a drawing convention.]
  # each pot: r ≈ 0.018*W, on a stem 0.030*H tall.
  # At FAR-layer scale, drop the pots entirely — they alias to fuzz.
```

**Taper sanity check.** For an 11-tier tower going from `W` to `0.50W`, a *uniform* per-tier ratio would be `0.50^(1/10) = 0.933` — i.e. **each tier ≈ 0.93 the width of the one below.** [DERIVED, from an [ESTIMATED] `W_top`.] For a 9-tier tower, `0.50^(1/8) = 0.917`. For a 7-tier tower, `0.50^(1/6) = 0.891`. Use these as the fallback if you implement a simple linear/geometric taper instead of the `pow` curve above. **Shorter towers taper harder per tier** — this is why a 7-tier gopuram looks stubbier and steeper than an 11-tier one, and it is the main thing that distinguishes them at silhouette scale.

### 0.4 The Pallava vimana construction algorithm

Mahabalipuram is Pallava, not Nayaka. A **vimana** is a different shape from a gopuram and must not be drawn with the same generator:

- **Square** in plan (a gopuram is oblong) — so it reads as a *point*, not a *wall*
- Steeper: it is a **stepped pyramid**, not a battered tower
- Crowned by a **rounded/octagonal śikhara over a circular neck (grīva)**, not a transverse barrel vault [SOURCED — Wikipedia, *Shore Temple*: the smaller shrine is "a double storied structure with a stepped pyramidal tower with an octagonal *shikhara*… over a circular *griva*"; *Dharmaraja Ratha*: "a terraced pyramidal tower" with "an octagonal *shikhara* (pinnacle) at the top"]
- A single **kalasa + finial** above the śikhara, not a row [SOURCED — Shore Temple: "*kalasa* and finial are fitted above the *shikhara*"]

```
VIMANA(H, W, N):
  plinth_h = 0.15 * H          # [ESTIMATED]
  body_h   = 0.55 * H          # the storeyed pyramid
  neck_h   = 0.10 * H          # circular griva — draw as a narrow waist
  sikh_h   = 0.14 * H          # octagonal/domical cap
  finial_h = 0.06 * H          # kalasa: a small onion + spike

  # storeys: N tiers over body_h, each tier width
  #   w_i = W * pow(0.80, i)     [ESTIMATED] — much harder taper than
  #   a gopuram. This is the key visual difference: a vimana closes
  #   to a point, a gopuram stops at a flat vaulted top.
  # each tier carries a HORIZONTAL CORNICE (kapota) — draw as a
  # thin outward lip, giving the pyramid a "stacked plates" edge.
  # neck: waist to 0.30*W, VERTICAL for neck_h.
  # sikhara: from the neck, bulge out to 0.46*W then close over the
  # top as a flattened dome (an octagon in plan reads as a slightly
  # faceted dome in elevation — 3 flat facets across the top arc).
```

**The waist is the whole trick.** A Pallava vimana pinches in at the neck before flaring back out into the śikhara. That single inflection — narrow, then wider, then closed — is what makes Mahabalipuram unmistakable and is what nothing else in this document has. Do not smooth it out.

---

## 1. SCROLL ORDER — the journey

### Recommended: **EAST → WEST** (coast to hills), left to right.

| # | City | Approx. longitude | Terrain reading |
|---|---|---|---|
| 1 | **Chennai** | 80.27° E | sea horizon, dead flat |
| 2 | **Mahabalipuram** | 80.19° E | sea horizon, dead flat, dunes |
| 3 | **Kanchipuram** | 79.70° E | flat plain, distant low rise |
| 4 | **Gingee** | 79.40° E | isolated granite domes erupting from plain |
| 5 | **Vellore** | 79.13° E | broken hill range on the skyline |
| 6 | **Tiruvannamalai** | 79.07° E | one enormous conical mountain |

[SOURCED — longitudes are standard geographic fact; the ordering is monotone east-to-west.]

**Why this ordering reads naturally — three reasons that all point the same way:**

1. **The horizon rises.** The FAR layer's amplitude grows monotonically across the scroll: a flat sea line at Chennai, → nothing at Kanchipuram, → three abrupt granite hills at Gingee, → a broken range at Vellore, → the single 814m cone of Arunachala filling the panel at Tiruvannamalai. The user experiences the land *lifting* as they scroll. This is free narrative — it requires no copy to explain it.

2. **The light travels with the sun.** Left edge = east = dawn over the Bay of Bengal. Right edge = west = dusk behind the mountain. A single sky gradient can rotate hue across all six panels without ever contradicting itself. Going the other way (west→east) would mean scrolling *into* the sunrise, which fights the reader's instinct.

3. **The economy inverts, meaningfully.** You start at the port and the IT corridor and end in the agricultural interior — which is precisely the axis a state startup platform is trying to bridge. The background argues the product's thesis without a word of copy.

**Alternative if you need a shorter scroll:** drop Gingee (weakest monument recognition, most redundant with Vellore) and run Chennai → Mahabalipuram → Kanchipuram → Vellore → Tiruvannamalai. The rising-horizon logic survives intact.

**Do not** reorder to put Tiruvannamalai in the middle. Arunachala is the largest silhouette in the set by a wide margin; anything after it is an anticlimax. It must be last.

### City captions (3–5 words, founder-economic)

| City | Caption |
|---|---|
| Chennai | *auto, IT, ports, fintech* |
| Mahabalipuram | *coastal tourism, sculpture, OMR corridor* |
| Kanchipuram | *silk weaving, temple economy* |
| Gingee | *agri, sugar, groundnut belt* |
| Vellore | *leather, healthcare, engineering campuses* |
| Tiruvannamalai | *pilgrim economy, agri, handloom* |

[ESTIMATED — these are well-known regional associations, not figures from an economic survey. Vellore's leather cluster (Ambur/Ranipet), CMC hospital and VIT are the standard three; Kanchipuram silk is the standard one. Verify against a TN industrial policy document before shipping as claims.]

---

## 2. MAHABALIPURAM

**Panel scale:** 1 pu ≈ 0.30 ft at MID layer. Shore Temple main vimana = 200 pu tall.

### 2.1 Shore Temple — MID layer, the hero

**Silhouette description.** Two pyramidal towers of unequal height standing on a low walled platform, the taller one behind and to the right (east), the shorter in front and to the left (west), with a low flat-roofed shrine bridging the gap between them. Each tower is a square stepped pyramid that pinches to a narrow circular neck and then swells into a flattened octagonal dome, capped by a spike. The silhouette's dominant read is **two sharp cones of different sizes sharing one horizontal base** — a shape no other Indian monument produces. The boundary wall running left and right from the platform is topped with a repeating row of seated bull (Nandi) lumps, which at silhouette scale reads as a **dotted/crenellated line**, not as animals.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Main vimana total height | 60 ft (18 m) | [SOURCED] |
| Platform | 50 ft (15 m) square | [SOURCED] |
| Main vimana storeys | 5 | [SOURCED] |
| Smaller (west) vimana storeys | 3 | [SOURCED] |
| Smaller vimana height | ≈ 34 ft — 0.57× the main | [ESTIMATED] |
| Main vimana base width | ≈ 28 ft (0.56 × platform) | [ESTIMATED] |
| Main vimana height : own base width | ≈ 2.15 : 1 | [DERIVED, from an estimated base] |
| Per-storey width taper | ≈ 0.80× per tier | [ESTIMATED] |
| Middle Vishnu shrine | low, flat, roofless — its tower is missing | [SOURCED] |

Draw as: `VIMANA(H=200pu, W=93pu, N=5)` for the main; `VIMANA(H=114pu, W=62pu, N=3)` for the western. Set them **75 pu apart centre-to-centre**, taller on the right, with a flat block 40 pu tall spanning between them. [ESTIMATED spacing.]

**Distinguishing feature.** The **height mismatch plus the empty gap**. Every other temple in this document is symmetrical or single-towered. Shore Temple is a deliberate asymmetric pair with a *headless* third shrine sitting in the valley between them — a low flat notch where a tower should be. If you draw two matched towers, you have drawn a generic temple. The notch is the signature.

**Layer depth.** **MID.** It should sit at the panel's optical centre with sea (FAR) behind it and rocks/palms (FORE) in front.

**Honest uncertainty.** The 60 ft / 50 ft figures are consistent across sources. The *smaller* tower's height is nowhere stated — I derived 0.57× from the 3-vs-5 storey ratio and the vimana taper, which is a reasonable but unverified inference. One tourism source claims the vimana "rises a massive seventy metres," which is flatly inconsistent with the 18 m figure and with the surviving building; I have discarded it. Do not use 70 m.

### 2.2 Pancha Rathas — FORE layer, or a second MID beat

**Silhouette description.** Five small monolithic shrines in a row on a common plinth, each with a **completely different roof form** — that variety *is* the monument. Left to right: a square thatched-hut roof with curved, drooping eaves; a small square pyramid; a long **barrel-vaulted wagon roof** lying on its side like an upturned boat; a tall three-tier pyramid with an octagonal cap; and an **apsidal, elephant-back roof** (a half-cylinder closed at one end by a curved hood). A free-standing monolithic elephant stands beside the last.

**Proportions.** These are unusually well sourced:

| Ratha | Base plan | Height | Roof form | Tag |
|---|---|---|---|---|
| **Draupadi** | 11 × 11 ft (3.4 × 3.4 m) | 18 ft (5.5 m) | square hut, curved thatch ("*bangla*" — a Bengal hut) | [SOURCED] |
| **Arjuna** | 11.5 × 16 ft (3.5 × 4.9 m) | 20 ft (6.1 m) | small storeyed pyramid | [SOURCED] |
| **Bhima** | 42 × 24 ft (12.8 × 7.3 m) | 25 ft (7.6 m) | **barrel-vaulted**, oblong, 2 floors | [SOURCED] |
| **Dharmaraja** | 28 × 28 ft (8.5 m sq) | 35 ft (10.7 m) | 3-tier pyramid + **octagonal śikhara** | [SOURCED] |
| **Nakula-Sahadeva** | not found | not found | **apsidal**, 2 tiers, "back of an elephant" | [SOURCED (form)], dims [ESTIMATED] ≈ 18 × 11 ft, 16 ft high |

**Derived ratios you can draw with:**
- Dharmaraja **height : base width = 35 : 28 = 1.25 : 1** [DERIVED, both sourced]. This is the single most reliable Pallava vimana proportion in the whole document — use it to sanity-check the Shore Temple.
- Bhima **length : width : height = 42 : 24 : 25 ≈ 1.68 : 0.96 : 1** [DERIVED, all sourced]. Note it is *wider than it is tall* — draw it low and long.
- Draupadi is a **1 : 1 square plan, height 1.64× its width** [DERIVED, both sourced], but roughly half that height is roof.

They stand on "a common mounted plinth which is north–south oriented with a slight slope" [SOURCED]. Draw the plinth as a single continuous slab with a 2–3 pu tilt.

**Distinguishing feature.** The **barrel-vaulted Bhima Ratha lying horizontally next to the pointed Dharmaraja Ratha**. Horizontal cylinder + vertical pyramid, side by side, same plinth. That pairing exists nowhere else.

**Layer depth.** **FORE** (cropped, large, at the panel's right edge as the scroll leaves Mahabalipuram) — or promote to a second MID group if you want a two-beat Mahabalipuram panel. The rathas are small buildings; at MID scale they must be drawn *close* to the camera or they vanish.

**Honest uncertainty.** Only Nakula-Sahadeva lacks dimensions; its *form* (apsidal, elephant-back, two-tier) is well sourced, so the shape is safe and only the size is guessed. Source disagreement exists on the row order; Wikipedia does not state the north–south sequence. The order I list above is the conventional one but **treat the ordering as [ESTIMATED]** — if it matters, verify before captioning.

---

## 3. KANCHIPURAM

**Panel scale:** 1 pu ≈ 0.30 ft. Ekambareswarar gopuram = 640 pu tall — this is the tallest object in the first three panels and should overflow the panel's upper edge.

### 3.1 Ekambareswarar Rajagopuram — MID layer, the hero

**Silhouette description.** A single enormous gopuram: a heavy vertical granite block at the base carrying a tapering, gently concave storeyed tower, its edges serrated by eleven projecting cornices, stopping abruptly in a flat-topped barrel vault studded with a row of pot finials. It does not come to a point. The profile is a **truncated, slightly waisted trapezoid** — the sides bow inward as they rise and then stop dead.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Height | 192 ft / 58.5 m (sources range 57–59 m) | [SOURCED] |
| Storeys | 11 | [SOURCED] |
| Base width | not found — use ≈ 120 ft | [ESTIMATED, by analogy to Annamalaiyar's 1.61:1] |
| Height : base width | ≈ 1.60 : 1 | [ESTIMATED] |
| Per-tier taper | ≈ 0.93× | [DERIVED from an estimated `W_top = 0.50W`] |
| Temple compound | over 23 acres (93,000 m²) | [SOURCED] |
| Gateway towers in complex | 4 | [SOURCED] |

Draw as `GOPURAM(H=640pu, W=400pu, N=11)`.

**Distinguishing feature.** **Sheer scale relative to a flat horizon, and the compound wall.** Kanchipuram has no hills — the Ekambareswarar gopuram is the only vertical thing for miles. Emphasise this by drawing an extremely long, low, unbroken **compound wall** running the full 1000 pu width of the panel at about 60 pu high, with the gopuram punching through it. The wall-to-tower ratio (roughly 1 : 10) is what says "23-acre temple city" rather than "one tower."

**Layer depth.** **MID** for the Rajagopuram. Put **two or three smaller gopuram tops** (the complex has four gateway towers [SOURCED]) in the **FAR** layer at 0.35–0.5× the hero's height, offset left and right, half-hidden behind the wall — this instantly reads as a temple *town*.

### 3.2 Kailasanathar Temple — FORE layer

**Silhouette description.** Small, low, and horizontal — the opposite of everything else in this document. A modest square pyramidal vimana with a small dome at the summit, sitting behind a long low rectangular compound wall whose **inner face is lined with a continuous row of small cells**, and with a separate small detached gate-shrine standing in front of it. The read is **a low wall with a rhythm of niches, one small pointed roof rising just above it.** It is deliberately *quiet*.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Vimana storeys | 4 | [SOURCED] |
| Vimana plan | square, pyramidal, small dome-shaped roof at summit | [SOURCED] |
| Small shrines in the compound wall niches | 58 | [SOURCED] |
| Shrines around the main sanctum | 9 (7 outside, 2 flanking the entrance) | [SOURCED] |
| Vimana height | **not found in any source** | — |
| Height : width | ≈ 1.15 : 1 | [ESTIMATED] |
| Overall plan | rectangular enclosure, dimensions not found | [SOURCED (shape only)] |

Draw as `VIMANA(H=90pu, W=78pu, N=4)`, sitting behind a wall 1000 pu long × 26 pu high, the wall's top edge broken by **a repeating 58-count niche rhythm** — at silhouette scale, render this as evenly-spaced small square notches, ~8 pu wide on a ~16 pu pitch. You will not fit 58 across the panel; use the *rhythm*, not the count.

**Distinguishing feature.** **Horizontality and the niche rhythm.** Every other structure here is a tower. Kailasanathar is a *ground plane* — the earliest and lowest building in the set. Its signature is the long dotted wall, not the vimana. Also note the material contrast (granite foundation, sandstone superstructure) [SOURCED] — irrelevant to silhouette but it means the profile is *softer and more eroded* than granite buildings; you can round the corners very slightly.

**Layer depth.** **FORE**, drawn low and wide across the bottom of the Kanchipuram panel, in front of and beneath the Ekambareswarar gopuram. The scale contrast (a 90 pu building in front of a 640 pu one) is the panel's entire composition.

**Honest uncertainty.** Real height unknown. The "four-storey vimana" is well sourced but one source says "many levels rising proportionately," so the storey count may be read differently by different observers. The 58-shrine and 9-shrine counts are solid.

---

## 4. CHENNAI

Chennai is the only panel that is **not** temple-led. It is a **skyline collage** — four unrelated silhouettes read left-to-right as a city. Do not try to make them one building.

**Panel scale:** 1 pu ≈ 0.28 ft.

### 4.1 Kapaleeshwarar gopuram (Mylapore) — MID layer, the hero

**Silhouette description.** A compact, steep gopuram — noticeably stubbier than Ekambareswarar because it packs nine tiers into a shorter tower, so the taper per tier is harder and the profile steeper. Flat barrel-vaulted top with pot finials. Because it is a 1906 stucco tower rather than a medieval granite one, its cornice lips are **deeper and more sharply projecting**, giving a more strongly serrated silhouette edge.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| East gopuram height | ~40 m (~131 ft) per Wikipedia; **120 ft** per several other sources | [SOURCED — but conflicting, see below] |
| Tiers / compartments | 9 | [SOURCED] |
| Built | 1906, stucco figures | [SOURCED] |
| West gopuram | smaller, faces the tank; height not stated | [SOURCED (relative only)] |
| Temple tank | 190 m × 143 m, 16-pillared granite-roofed mandapam at centre | [SOURCED] |
| Base width | not found — use ≈ 82 ft | [ESTIMATED] |
| Height : base width | ≈ 1.55 : 1 | [ESTIMATED] |
| Per-tier taper (9 tiers) | ≈ 0.92× | [DERIVED from estimated `W_top`] |

**⚠ Source conflict, unresolved.** Wikipedia says "about 40 m high" (131 ft); multiple other sources say "120 ft." These differ by ~9%. The 9-tier count is consistent. **Recommendation: draw to 120 ft and note the discrepancy** — 120 ft is the more commonly repeated figure and the difference is invisible at silhouette scale. Do not present either as certain.

Draw as `GOPURAM(H=430pu, W=277pu, N=9)`.

**Distinguishing feature.** Its **squatness relative to Ekambareswarar** — 9 tiers instead of 11, at roughly 62% the height. If both appear in the same scroll (they do), the user should feel Kanchipuram's tower is *taller and more slender* and Chennai's is *closer and blockier*. Also, the **tank**: a large rectangular water body with a small square pillared pavilion floating at its centre is a Mylapore-specific FORE element and reads instantly as "temple tank."

**Layer depth.** **MID.**

### 4.2 Chennai (Madras) Lighthouse — MID/FORE layer

**Silhouette description.** A tall, slender **triangular-plan** tower — so in elevation the sides are near-vertical with a very slight batter — topped by a **double gallery** (two stacked projecting rings, the lower wider) and a lantern housing with a small dome and spike. The banded red-and-white paint is invisible in silhouette; what survives is **an unornamented vertical shaft with two sharp horizontal flanges near the top.** That double flange is the whole read.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Tower height | 45.72 m (150.0 ft) | [SOURCED] |
| Focal plane above mean sea level | 57 m (187 ft) | [SOURCED] |
| Storeys | 11 | [SOURCED] |
| Plan | triangular cylindrical, concrete | [SOURCED] |
| Top: lantern + **double** gallery | yes | [SOURCED] |
| Shaft width at base | ≈ 7.6 m | [ESTIMATED] |
| Height : base width | ≈ 6 : 1 | [ESTIMATED] |
| Gallery projection | ≈ 1.45× shaft width | [ESTIMATED] |
| Built | 1976, opened Jan 1977 | [SOURCED] |

Draw as: a shaft 535 pu tall, 90 pu wide at base tapering to 72 pu at the gallery; lower gallery ring 130 pu wide × 14 pu; a 30 pu gap; upper gallery 112 pu wide × 12 pu; lantern 70 pu wide × 45 pu with a shallow dome and a 20 pu spike.

**Distinguishing feature.** **Two galleries, not one.** Almost every drawn lighthouse has a single gallery. Chennai's has a double gallery [SOURCED] — draw both rings with a visible gap and the silhouette becomes specifically Madras.

**Layer depth.** **FORE**, at the panel's left edge (seaward), partially cropped. Or **MID** if Kapaleeshwarar is moved right.

### 4.3 Napier Bridge — FORE layer

**Silhouette description.** A horizontal deck carried on a repeating series of **bowstring arches** — each span is a shallow arc *above* the deck line, tied by the straight deck below it, with vertical hangers between. The read is **a row of identical low humps sitting on a dead-straight line**, like a very flat sine wave clipped at the baseline. Arches appear on both sides of the deck.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Total length | 138 m (453 ft) | [SOURCED] |
| Number of spans | 6 | [SOURCED] |
| Arch type | bowstring, on either side | [SOURCED] |
| Length per span | 23 m | [DERIVED, both sourced] |
| Arch rise | ≈ 4.2 m — rise : span ≈ 1 : 5.5 | [ESTIMATED] |
| Vertical hangers per span | 5–7 | [ESTIMATED] |

Draw as: deck line at `y = 520`, six arcs of 167 pu span each (1000 pu total), rise 30 pu, with 5 vertical hangers per span. This is a **pure geometric primitive** — one arc path, translated six times. Cheapest element in the entire background.

**Distinguishing feature.** The **six-hump repetition at a very flat rise ratio.** Most drawn bridges are either one big arch or a suspension catenary. Six shallow identical bowstrings is Napier. (Note: it has been painted in rainbow colours since 2022 — if the design ever moves off monochrome, this is the one element with a licence to be polychrome.)

**Layer depth.** **FORE**, running along the very bottom of the Chennai panel, cropped by both edges.

### 4.4 Senate House / Indo-Saracenic domes — FAR layer

**Silhouette description.** A long horizontal block with **four onion domes at its four corners**, each on a short drum, each with a pinched neck and a pointed finial. Between and behind them, a taller central mass. In silhouette this is a **flat roofline punctuated by four bulbs** — the bulb profile (wider than its neck, coming to a point) is the entire Indo-Saracenic signal.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Corner towers crowned by onion domes | 4 | [SOURCED] |
| Composition | symmetrical, "in a Byzantine manner" | [SOURCED] |
| Built | 1874–1879, Robert Chisholm | [SOURCED] |
| Building height | **not found** | — |
| Dome height : drum width | ≈ 1.3 : 1 | [ESTIMATED] |
| Dome max width : neck width | ≈ 1.35 : 1 (the bulge) | [ESTIMATED] |
| Block length : height | ≈ 4 : 1 | [ESTIMATED] |

Onion dome path recipe: from the neck at width `n`, bulge outward to `1.35n` at 35% of the dome's height, return to `0.55n` at 82%, then close to a point; add a 0.25×height finial spike. [ESTIMATED — this is a generic onion profile, not a measurement of Senate House.]

**Distinguishing feature.** **Four corner bulbs on one long low roof.** Madras High Court, by contrast, reads as *one* tall central dome-on-a-tower with minarets — if you want both, use Senate House's four-corner rhythm in FAR and a single taller domed tower at the panel's far right as the High Court.

**Layer depth.** **FAR.** Draw at 0.35× the Kapaleeshwarar gopuram's height, low opacity, no internal detail — a dark ribbon of city with four bumps.

**Honest uncertainty.** I found **no height figure** for Senate House or its towers, and no dome diameter. All Senate House proportions above are invented. The *four corner onion domes* and the symmetry are firmly sourced; use the arrangement, distrust the numbers. Madras High Court's dome is likewise unmeasured here — the only number I encountered was a "160-ft-tall lighthouse tower" whose lamps were later moved to the High Court dome, which tells you nothing about the dome itself. Do not repurpose that 160 ft.

---

## 5. TIRUVANNAMALAI

The strongest panel in the set. Save it for last.

**Panel scale:** 1 pu ≈ 0.55 ft — this panel needs a *coarser* scale than the others because the mountain is two orders of magnitude larger than the temple.

### 5.1 Arunachala hill — FAR layer, and the panel's true subject

**Silhouette description.** A single, isolated, near-**conical** mountain rising directly out of a flat plain with no foothills and no neighbouring range. Its profile is a broad triangle with slightly convex flanks (steeper near the summit, flattening as it meets the plain) and a rounded, slightly asymmetric apex — not a sharp peak. It fills the panel. Everything else in Tiruvannamalai is drawn *against* it.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Summit elevation | 814 m (2,671 ft) above sea level | [SOURCED] |
| Town elevation | ~170–200 m | [ESTIMATED] |
| **Visible rise above the plain** | **≈ 620–645 m (~2,050 ft)** | [DERIVED, from a sourced summit and an estimated base] |
| Base span across | ≈ 3× its visible height | [ESTIMATED] |
| Profile | broad cone, convex flanks, rounded apex | [ESTIMATED from description] |

Draw as a single path: base 1000 pu wide, apex at 340 pu high, offset the apex 8% right of centre for asymmetry, and use **two quadratic curves** (left flank control point pulled *outward/down*, right flank control point pulled *outward/down*) so both flanks bulge convex rather than running straight. Round the apex with a 20 pu radius arc.

**Critical: use the 620 m rise, not the 814 m elevation.** 814 m is height above *sea level*; the town sits ~180 m up. Drawing 814 m against a groundline at the town would make the hill ~30% too tall. This is the most likely single error in the whole document and it is easy to make.

**Distinguishing feature.** **Total isolation.** Arunachala has no range behind it and no foothills — it is one mass on an empty plain. Every other hill in this set (Vellore, Gingee) comes in company. If you draw a second hill anywhere in this panel, you have destroyed the identification.

**Layer depth.** **FAR** — but at unusually high opacity for a FAR element (0.20–0.28) because it is the panel's protagonist, not its backdrop.

### 5.2 Annamalaiyar Temple Rajagopuram — MID layer

**Silhouette description.** The largest gopuram in this document — eleven tiers, tapering, flat barrel-vaulted top — standing at the *foot* of the mountain so that the mountain's flank rises directly behind and above it. The composition is **man-made triangle in front of natural triangle**, with the gopuram's hard stepped edge contrasted against the hill's smooth curve. Three further gopurams stand lower and further back.

**Proportions.** This is the best-sourced tower in the document:

| Element | Value | Tag |
|---|---|---|
| Eastern (Raja) gopuram height | **66 m (217 ft)** | [SOURCED] |
| Storeys | **11** | [SOURCED] |
| Granite base footprint | **135 ft × 98 ft (41 m × 30 m)** | [SOURCED] |
| **Height : base long-face width** | **217 : 135 = 1.61 : 1** | [DERIVED, both sourced] |
| **Base depth : base width** | **98 : 135 = 0.73 : 1** | [DERIVED, both sourced] |
| Top width | not found — use 0.50 × base | [ESTIMATED] |
| Per-tier taper | ≈ 0.93× | [DERIVED from estimated `W_top`] |
| Gateway towers in complex | 4 | [SOURCED] |
| Complex area | 10 hectares | [SOURCED] |
| Built | begun by Krishnadevaraya (1509–29), completed by Sevappa Nayaka (1532–80) | [SOURCED] |

**Use the 1.61 : 1 ratio as the master ratio for every gopuram in this project.** It is the only height:base ratio in this set derived entirely from sourced numbers. Where I have estimated a base width for Ekambareswarar, Kapaleeshwarar or Jalakandeswarar, I derived it from this ratio — so if you improve any one of them with a real measurement, revisit the others.

Draw as `GOPURAM(H=395pu, W=245pu, N=11)` at this panel's coarser scale.

**Distinguishing feature.** **The tower against the mountain, at a specific size ratio.** The gopuram at 217 ft against a hill rising ~2,050 ft means the temple is **roughly 1/9.5 the height of the hill** [DERIVED]. Get that ratio right and the image is unmistakable; make the temple too big and it becomes a generic temple-with-hill.

**Layer depth.** **MID.**

### 5.3 Foreground

**FORE:** the girivalam (circumambulation) road — draw a low continuous line of small roadside shrines and palmyra palms across the bottom. [ESTIMATED — the road is a real feature; its silhouette treatment is my design choice.]

---

## 6. VELLORE

**Panel scale:** 1 pu ≈ 0.32 ft.

### 6.1 Vellore Fort ramparts — MID layer, the hero

**Silhouette description.** A long, low, absolutely horizontal granite wall with **round drum towers** projecting from it at intervals, alternating with **rectangular projections** — so the top edge is flat but the *plan* pushes in and out, which in elevation reads as a rhythm of full-height vertical bands of different widths. In front of the wall is a **wide flat band of still water** (the moat), which in silhouette is a horizontal void separating the fort from the foreground. The fort is emphatically wider than it is tall.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Enclosed area | 133 acres (0.54 km²) | [SOURCED] |
| Site altitude | 220 m (720 ft) | [SOURCED] |
| Tower plan | **round towers and rectangular projections**, main rampart 14th c., granite | [SOURCED] |
| Wall height | "up to 30 ft", walls "20 ft thick", double walls | [SOURCED — secondary sources only; **Wikipedia does not corroborate**] |
| Moat width | "wide"/"broad"; 80 ft figure belongs to *Gingee*, not Vellore | see note |
| Bastions | at regular intervals, "projecting irregularly" | [SOURCED] |
| Wall length : height ratio in silhouette | ≈ 20 : 1 | [ESTIMATED] |
| Round tower diameter | ≈ 1.6 × wall height | [ESTIMATED] |
| Tower spacing | ≈ 6 × wall height | [ESTIMATED] |

Draw as: wall 1000 pu long × 48 pu high (30 ft at scale ≈ 94 pu — but compress to 48 pu so it stays a *base* for the temple; note this is an artistic compression, not the real ratio). Round drums 77 pu wide, projecting 6 pu above the wall line, at ~290 pu intervals. Moat = a horizontal band 70 pu deep in front, rendered as flat fill with a single specular line.

**⚠ Do not copy Gingee's moat width onto Vellore.** The "80 feet (24 m) wide moat" figure I found belongs to Gingee Fort. Vellore's moat is described only qualitatively in the sources I reached.

**Distinguishing feature.** **Round towers on a flat wall behind a wide water band.** Gingee's fortification climbs hills; Vellore's is on flat ground with a full water moat. Water + horizontality + round drums = Vellore.

### 6.2 Jalakandeswarar Temple gopuram — MID layer, rising from inside the fort

**Silhouette description.** A seven-tier gopuram standing **inside** the fort walls, so its base is hidden and only its upper two-thirds clears the rampart. Because it has only seven tiers it tapers harder per tier than the eleven-tier towers — the profile is noticeably **steeper and more pointed**, closer to a truncated cone than Ekambareswarar's near-vertical batter.

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Storeys | **7** | [SOURCED] |
| Height | "over 100 ft" / "over 30 m" | [SOURCED — approximate, sources hedge with "over"] |
| Base width | not found — use ≈ 65 ft | [ESTIMATED, via the 1.61:1 Annamalaiyar ratio] |
| Per-tier taper (7 tiers) | ≈ 0.89× | [DERIVED from estimated `W_top`] |

Draw as `GOPURAM(H=325pu, W=203pu, N=7)`, positioned so `y = 520` (groundline) sits **behind** the rampart — i.e. draw the fort wall *over* the gopuram's lower 48 pu.

**Distinguishing feature.** **A temple tower inside a fort.** This composition — sacred tower rising from behind military ramparts, reflected in a moat — exists in this set only at Vellore. It is the whole panel.

**Layer depth.** Fort wall and gopuram are both **MID**, deliberately interlocking. **FAR:** the broken hill range that surrounds Vellore ("a broken mountain range" [SOURCED]) — draw as a low, jagged, multi-peaked ridge at ~90 pu, in contrast to Arunachala's single smooth cone. **FORE:** the moat's near bank and a row of tamarind/rain trees.

**Honest uncertainty.** The 30 ft wall / 20 ft thick figures come from tourism and blog sources, not archaeological survey. The Wikipedia article gives area and altitude only and explicitly does not corroborate wall dimensions. Treat the wall height as [SOURCED but weakly].

---

## 7. GINGEE

**Panel scale:** 1 pu ≈ 0.55 ft (match Tiruvannamalai — this is a landscape panel).

### 7.1 The three hills — FAR layer, the hero

**Silhouette description.** Three separate, abrupt, bald granite domes rising from a flat plain, unconnected at their bases, with a thin fortification wall visibly **running up and over each summit** and looping across the ground between them. The hills are rounded — weathered granite monoliths, not peaks — so their profiles are **arcs, not triangles**. The read is **three humps of unequal size stitched together by a single continuous line.**

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Number of citadels | 3 — Rajagiri, Krishnagiri, Chandrayandurg | [SOURCED] |
| Arrangement | Krishnagiri **north**, Rajagiri **west**, Chandrayandurg **southeast** | [SOURCED] |
| Rajagiri height | **800 ft (240 m)** — the highest and largest | [SOURCED] |
| Krishnagiri | "smaller and lower than Rajagiri" | [SOURCED — relative only] |
| Chandrayandurg | height not stated | — |
| Fort wall length | 13 km | [SOURCED] |
| Enclosed area | 11 km², triangular | [SOURCED] |
| Moat width | 80 ft (24 m) | [SOURCED] |
| Rajagiri drawbridge | 20 ft long × 6 ft wide, over a **20 m deep chasm** | [SOURCED] |
| Krishnagiri height | ≈ 0.65 × Rajagiri | [ESTIMATED] |
| Chandrayandurg height | ≈ 0.55 × Rajagiri | [ESTIMATED] |
| Hill profile | rounded dome, base ≈ 2.5× height | [ESTIMATED] |

⚠ **Source conflict:** one source says Rajagiri is "at an elevation of about 800 **meters**"; others say "800 **feet** (240 metres)". 800 ft / 240 m is the internally consistent pair and is repeated more often. **Use 240 m.**

Draw as: three arc-based domes on a common groundline — Rajagiri 240 pu high × 600 pu base (place right-of-centre, the "west" hill, closest to the viewer's forward direction of travel); Krishnagiri 156 pu × 390 pu (place left, "north"); Chandrayandurg 132 pu × 330 pu (place centre-right and further back). Overlap them slightly in x but never let their outlines merge — the *gaps between* them are the identification.

**Distinguishing feature.** **Exactly three, unequal, unconnected, with one thin wall line running over all of them.** Draw the wall as a 2 pu stroke that follows each hill's upper contour ~15 pu inside the silhouette edge, then drops to the plain and runs horizontally between hills. That single continuous line is what turns three rocks into a fort.

### 7.2 Kalyana Mahal — MID/FORE layer

**Silhouette description.** A **square tower of seven storeys with a pyramidal roof**, standing alone in the flat ground between the hills, surrounded by a low square courtyard block. Each storey is slightly recessed from the one below, so the tower steps inward like a small ziggurat, and it terminates in a simple pointed pyramid — **no barrel vault, no kalasam row, no dome.**

**Proportions.**

| Element | Value | Tag |
|---|---|---|
| Storeys | **7** | [SOURCED] |
| Plan | square | [SOURCED] |
| Roof | pyramidal | [SOURCED] |
| Setting | large square court with rooms, tower rising in the middle | [SOURCED] |
| Height | not found | — |
| Height : base width | ≈ 3.2 : 1 | [ESTIMATED] |
| Per-storey width taper | ≈ 0.95× (very slight) | [ESTIMATED] |
| Pyramidal roof height | ≈ 0.18 of total | [ESTIMATED] |

Draw as: base 60 pu wide, 7 stacked bands of ~26 pu each with a 5% inward step and a small projecting eave at each level, total shaft 182 pu, then a pyramid 40 pu tall closing to a point. Surround with a courtyard block 210 pu wide × 34 pu high.

**Distinguishing feature.** **A seven-storey square tower with a plain pyramid on top, standing on flat ground with nothing else near it.** It is the only tall *secular* tower in this entire document — no finials, no vault, no dome. Silhouetted against the gap between two hills, it is unmistakable.

**Layer depth.** **MID** (against the hills, which are FAR). **FORE:** boulder outcrops — Gingee's plain is littered with loose granite boulders; a scatter of large rounded lumps cropped at the panel's bottom edge is cheap and highly characteristic of this landscape.

**Honest uncertainty.** No height for Kalyana Mahal anywhere. The seven-storey / square / pyramidal-roof description is solidly sourced and is enough to draw a correct *shape* at an incorrect *size*. Chandrayandurg's height is entirely guessed.

---

## 8. IMPLEMENTATION CHECKLIST

1. **Write `GOPURAM(H, W, N)` and `VIMANA(H, W, N)` first.** They cover 8 of the 14 monuments. Everything else is bespoke but simple.
2. **Master ratio: 1.61 : 1** (height : base width) for gopurams — the only fully sourced one, from Annamalaiyar.
3. **Never taper a gopuram to a point.** It stops flat at ~0.50 of its base width and is capped by a transverse barrel vault. Getting this wrong is the most common way to draw a South Indian temple that reads as Thai or Khmer.
4. **Never give a Pallava vimana a barrel vault.** It has a circular neck and an octagonal dome. The two roof grammars must not be mixed.
5. **The kapota lip** (a small outward flare at the top of each tier) is what creates the serrated edge. Without it, both generators produce smooth cones and every monument looks identical.
6. **Arunachala uses 620 m of visible rise, not 814 m of elevation.**
7. **Path budget.** All fourteen silhouettes should fit in well under 30 KB of inline path data at 2 decimal places. Round all coordinates to 1 decimal; drop kalasams and hangers on the FAR layer; ship a single `<symbol>` per repeated element (arch span, round drum, kalasam pot, tier) and `<use>` it.
8. **Re-measure before shipping if accuracy matters:** the base widths of Ekambareswarar, Kapaleeshwarar and Jalakandeswarar; the heights of Kailasanathar's vimana, Senate House, and Kalyana Mahal; the ratha row order at Mahabalipuram; Vellore's wall and moat dimensions.

---

## Sources

- [Shore Temple — Wikipedia](https://en.wikipedia.org/wiki/Shore_Temple)
- [Pancha Rathas — Wikipedia](https://en.wikipedia.org/wiki/Pancha_Rathas)
- [Dharmaraja Ratha — Wikipedia](https://en.wikipedia.org/wiki/Dharmaraja_Ratha)
- [Nakula Sahadeva Ratha — Wikipedia](https://en.wikipedia.org/wiki/Nakula_Sahadeva_Ratha)
- [Arjuna Ratha — Wikipedia](https://en.wikipedia.org/wiki/Arjuna_Ratha)
- [Draupadi Ratha — Wikipedia](https://en.wikipedia.org/wiki/Draupadi_Ratha)
- [Bhima Ratha — Mahabalipuram.org](https://www.mahabalipuram.org/bhima-ratha-mahabalipuram/)
- [Kailasanathar Temple, Kanchipuram — Wikipedia](https://en.wikipedia.org/wiki/Kailasanathar_Temple,_Kanchipuram)
- [Ekambareswarar Temple (Kanchipuram) — Wikipedia](https://en.wikipedia.org/wiki/Ekambareswarar_Temple_(Kanchipuram))
- [Kapaleeshwarar Temple — Wikipedia](https://en.wikipedia.org/wiki/Kapaleeshwarar_Temple)
- [Gopuram — Wikipedia](https://en.wikipedia.org/wiki/Gopuram)
- [Chennai Lighthouse — Wikipedia](https://en.wikipedia.org/wiki/Chennai_Lighthouse)
- [Napier Bridge — Wikipedia](https://en.wikipedia.org/wiki/Napier_Bridge)
- [Senate House (University of Madras) — Wikipedia](https://en.wikipedia.org/wiki/Senate_House_(University_of_Madras))
- [Senate House, Madras, by Robert Fellowes Chisholm — The Victorian Web](https://victorianweb.org/art/architecture/chisholm/2.html)
- [Arunachala — Wikipedia](https://en.wikipedia.org/wiki/Arunachala)
- [Arunachalesvara Temple — Kiddle](https://kids.kiddle.co/Arunachalesvara_Temple)
- [Vellore Fort — Wikipedia](https://en.wikipedia.org/wiki/Vellore_Fort)
- [Vellore Fort — Tamil Nadu Tourism](https://www.tamilnadutourism.tn.gov.in/destinations/vellore-fort)
- [Jalakandeswarar Temple, Vellore — Wikipedia](https://en.wikipedia.org/wiki/Jalakandeswarar_Temple,_Vellore)
- [Gingee Fort — Wikipedia](https://en.wikipedia.org/wiki/Gingee_Fort)
- [Gingee — Wikipedia](https://en.wikipedia.org/wiki/Gingee)
- [Gingee Fort: Rajagiri Fort — PeakVisor](https://peakvisor.com/poi/gingee-fort-rajagiri-fort.html)
