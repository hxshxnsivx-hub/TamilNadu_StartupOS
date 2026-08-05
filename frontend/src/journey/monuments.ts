/* Tamil Nadu monuments as parametric silhouettes.
 *
 * Geometry from the sourced research in
 *   .kiro/specs/tamil-nadu-startupos/monuments-north.md
 *   .kiro/specs/tamil-nadu-startupos/monuments-south.md
 *
 * Two roof grammars, and they must never be mixed — confusing them is the
 * standard way to draw a South Indian temple that reads as Thai:
 *
 *   GOPURAM  concave batter, shallow taper (~0.93/tier), stops flat at about
 *            half its base width under a transverse barrel vault (śāla),
 *            crowned by a ROW of finials.
 *   VIMANA   straight pyramid sides, steep taper (0.90/tier at Thanjavur),
 *            pinching to a neck and swelling into ONE dome with ONE finial.
 *
 * Shared coordinate system: a 1000 × 600 panel with the groundline at y = 520.
 * Silhouettes are drawn as overlapping filled polygons in a single colour —
 * no boolean union is needed because the fill is flat.
 */

export const PANEL_W = 1000;
export const PANEL_H = 600;
export const GROUND = 520;

type Poly = string;

const poly = (pts: Array<[number, number]>): Poly =>
  pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("") + "Z";

const rect = (x: number, y: number, w: number, h: number): Poly =>
  poly([
    [x, y],
    [x + w, y],
    [x + w, y + h],
    [x, y + h],
  ]);

/**
 * A gopuram — the gateway tower.
 *
 * @param H total height  @param W base width  @param N number of tiers (talas)
 *
 * The vertical base block is what makes this read as a gopuram rather than a
 * generic pyramid; the kapota lip at each tier top is what produces the
 * serrated edge. Skip either and it becomes a smooth cone.
 */
export function gopuram(cx: number, baseY: number, H: number, W: number, N: number): Poly[] {
  const out: Poly[] = [];

  const baseH = 0.2 * H; // [ESTIMATED] 0.16–0.24
  const superH = 0.74 * H;
  const wTop = 0.5 * W; // [ESTIMATED] 0.45–0.55
  const p = 1.18; // >1 bows the sides inward — the concave batter

  out.push(rect(cx - W / 2, baseY - baseH, W, baseH));

  // tier heights decay slightly slower than widths; solve h0 so they sum to superH
  const decay = 0.93;
  let denom = 0;
  for (let i = 0; i < N; i++) denom += Math.pow(decay, i);
  const h0 = superH / denom;

  const widthAt = (i: number) => {
    const t = i / (N - 1);
    return wTop + (W - wTop) * Math.pow(1 - t, p);
  };

  let y = baseY - baseH;
  for (let i = 0; i < N; i++) {
    const hi = h0 * Math.pow(decay, i);
    const wb = widthAt(i);
    const wt = widthAt(Math.min(i + 1, N - 1));
    out.push(
      poly([
        [cx - wb / 2, y],
        [cx + wb / 2, y],
        [cx + wt / 2, y - hi],
        [cx - wt / 2, y - hi],
      ]),
    );
    // kapota: a small outward flare at the tier's top edge
    const lip = 0.03 * W;
    out.push(rect(cx - wt / 2 - lip, y - hi, wt + 2 * lip, 0.35 * hi));
    y -= hi;
  }

  // śāla — the barrel vault, drawn transversely, oversailing the top tier
  const salaW = 1.15 * wTop;
  const salaH = 0.06 * H;
  out.push(rect(cx - salaW / 2, y - salaH * 0.65, salaW, salaH * 0.65));
  out.push(
    poly([
      [cx - salaW / 2, y - salaH * 0.65],
      [cx - salaW / 2 + salaW * 0.12, y - salaH],
      [cx + salaW / 2 - salaW * 0.12, y - salaH],
      [cx + salaW / 2, y - salaH * 0.65],
    ]),
  );

  // a ROW of finials — the gopuram's signature, never a single one
  const n = 5;
  for (let k = 0; k < n; k++) {
    const fx = cx - salaW / 2 + (salaW * (k + 0.5)) / n;
    out.push(rect(fx - 0.006 * W, y - salaH - 0.035 * H, 0.012 * W, 0.035 * H));
  }
  return out;
}

/**
 * A vimana — the sanctum tower. Straight sides, one dome, one finial.
 * Thanjavur's taper of 0.90/tier is derived from a sourced 30.18 m base and
 * 7.77 m capstone over 13 tiers, and stepping it lands exactly on the measured
 * capstone — so it is self-consistent, not a guess.
 */
export function vimana(
  cx: number,
  baseY: number,
  H: number,
  W: number,
  N: number,
  taper = 0.9,
): Poly[] {
  const out: Poly[] = [];
  const baseH = 0.16 * H;
  out.push(rect(cx - W / 2, baseY - baseH, W, baseH));

  const superH = 0.62 * H;
  let denom = 0;
  for (let i = 0; i < N; i++) denom += Math.pow(0.94, i);
  const h0 = superH / denom;

  let y = baseY - baseH;
  let w = W;
  for (let i = 0; i < N; i++) {
    const hi = h0 * Math.pow(0.94, i);
    const wt = w * taper;
    out.push(
      poly([
        [cx - w / 2, y],
        [cx + w / 2, y],
        [cx + wt / 2, y - hi],
        [cx - wt / 2, y - hi],
      ]),
    );
    y -= hi;
    w = wt;
  }

  // neck, then ONE dome, then ONE finial
  const neckW = w * 0.72;
  const neckH = 0.05 * H;
  out.push(rect(cx - neckW / 2, y - neckH, neckW, neckH));
  y -= neckH;
  const domeW = w * 1.15;
  const domeH = 0.11 * H;
  out.push(
    poly([
      [cx - domeW / 2, y],
      [cx - domeW * 0.36, y - domeH * 0.72],
      [cx, y - domeH],
      [cx + domeW * 0.36, y - domeH * 0.72],
      [cx + domeW / 2, y],
    ]),
  );
  out.push(rect(cx - 0.008 * W, y - domeH - 0.07 * H, 0.016 * W, 0.07 * H));
  return out;
}

/** A long low compound wall — what says "temple city" rather than "one tower". */
export function wall(y: number, h = 46, from = 0, to = PANEL_W): Poly[] {
  const out = [rect(from, y - h, to - from, h)];
  for (let x = from + 24; x < to - 24; x += 58) {
    out.push(rect(x, y - h - 9, 26, 9)); // parapet rhythm
  }
  return out;
}

/** A hill. Arunachala's drawable rise is ~620 m, not its 814 m elevation —
 *  the town already sits ~180 m up, and using 814 makes it ~30% too tall. */
export function hill(cx: number, baseY: number, H: number, W: number): Poly[] {
  return [
    poly([
      [cx - W / 2, baseY],
      [cx - W * 0.22, baseY - H * 0.82],
      [cx, baseY - H],
      [cx + W * 0.26, baseY - H * 0.78],
      [cx + W / 2, baseY],
    ]),
  ];
}

/** The Nilgiri ridge. Eight named peaks span 2,375–2,637 m — only ~10%
 *  variation — so this is soft undulation, never alpine peaks. */
export function ridge(baseY: number, H: number): Poly[] {
  const pts: Array<[number, number]> = [[0, baseY]];
  const ks = [0.72, 0.9, 0.8, 1.0, 0.86, 0.94, 0.78, 0.88];
  ks.forEach((k, i) => pts.push([(PANEL_W * (i + 0.5)) / ks.length, baseY - H * k]));
  pts.push([PANEL_W, baseY]);
  return [poly(pts)];
}

/** Pamban: 14.4 m pier spacing against a 12.5 m deck (1.15 : 1), with the
 *  65.23 m bascule gap ≈ 4.5 normal bays. The rhythm-plus-one-interruption is
 *  why this is the only monument here still legible at 20 px. */
export function pamban(baseY: number, H = 78): Poly[] {
  const out: Poly[] = [];
  const deck = baseY - H * 0.42;
  out.push(rect(0, deck, PANEL_W, H * 0.13));
  const bay = 62; // 14.4 m pier spacing, scaled
  const gapStart = PANEL_W * 0.44;
  const gapW = bay * 4.5; // the bascule span
  for (let x = 0; x < PANEL_W; x += bay) {
    if (x > gapStart && x < gapStart + gapW) continue;
    out.push(rect(x + bay * 0.36, deck + H * 0.13, bay * 0.2, baseY - deck - H * 0.13));
  }
  // the lift span, raised
  out.push(rect(gapStart, deck - H * 0.34, gapW, H * 0.1));
  out.push(rect(gapStart, deck - H * 0.34, H * 0.08, H * 0.34));
  out.push(rect(gapStart + gapW - H * 0.08, deck - H * 0.34, H * 0.08, H * 0.34));
  return out;
}

/** A lighthouse — Chennai's Marina. Foreground punctuation. */
export function lighthouse(cx: number, baseY: number, H: number): Poly[] {
  const w = H * 0.13;
  return [
    poly([
      [cx - w, baseY],
      [cx - w * 0.55, baseY - H * 0.86],
      [cx + w * 0.55, baseY - H * 0.86],
      [cx + w, baseY],
    ]),
    rect(cx - w * 0.8, baseY - H * 0.95, w * 1.6, H * 0.09),
    rect(cx - w * 0.4, baseY - H, w * 0.8, H * 0.05),
  ];
}

/** Chettinad: horizontal and columned, the deliberate contrast to every
 *  vertical tower. No published dimensions exist — this is art direction. */
export function mansion(cx: number, baseY: number, H: number, W: number): Poly[] {
  const out = [rect(cx - W / 2, baseY - H * 0.52, W, H * 0.52)];
  const cols = 9;
  for (let i = 0; i < cols; i++) {
    const x = cx - W / 2 + (W * (i + 0.5)) / cols;
    out.push(rect(x - W * 0.012, baseY - H * 0.52, W * 0.024, H * 0.52));
  }
  // pediment
  out.push(
    poly([
      [cx - W * 0.3, baseY - H * 0.52],
      [cx, baseY - H * 0.78],
      [cx + W * 0.3, baseY - H * 0.52],
    ]),
  );
  return out;
}

// ---------------------------------------------------------------------------
// The journey. East to west, coast to interior: the land visibly lifts as you
// scroll, and the axis runs port-and-IT toward the agricultural interior —
// which is the axis the product itself is about.
// ---------------------------------------------------------------------------

export type Station = {
  id: string;
  city: string;
  ta: string;
  monument: string;
  economy: string;
  far: Poly[];
  mid: Poly[];
  fore: Poly[];
};

export const STATIONS: Station[] = [
  {
    id: "chennai",
    city: "Chennai",
    ta: "சென்னை",
    monument: "Kapaleeshwarar gopuram · Marina",
    economy: "Auto, IT, ports",
    far: [rect(0, GROUND - 8, PANEL_W, 8)],
    mid: gopuram(430, GROUND, 300, 186, 9),
    fore: lighthouse(790, GROUND, 150),
  },
  {
    id: "mahabalipuram",
    city: "Mahabalipuram",
    ta: "மாமல்லபுரம்",
    monument: "Shore Temple",
    economy: "Stone craft, tourism",
    far: [rect(0, GROUND - 6, PANEL_W, 6)],
    // twin vimanas, Pallava proportion 1.25 : 1 [SOURCED via Dharmaraja Ratha]
    mid: [...vimana(430, GROUND, 250, 200, 7, 0.86), ...vimana(600, GROUND, 175, 140, 6, 0.86)],
    fore: [],
  },
  {
    id: "thanjavur",
    city: "Thanjavur",
    ta: "தஞ்சாவூர்",
    monument: "Brihadeeswarar vimana",
    economy: "Delta agriculture, rice",
    far: [],
    // 13 tiers at the derived 0.90 taper — the vimana is taller than the
    // gopuram here, the reverse of every other TN temple
    mid: vimana(500, GROUND, 400, 240, 13, 0.9),
    fore: wall(GROUND, 40, 0, PANEL_W),
  },
  {
    id: "madurai",
    city: "Madurai",
    ta: "மதுரை",
    monument: "Meenakshi Amman — four gopurams",
    economy: "Textiles, trade, temple economy",
    far: [],
    // four near-equal towers: the composition, not the profile, is what
    // distinguishes Madurai from Srirangam or Rameswaram at this scale
    mid: [
      ...gopuram(200, GROUND, 330, 205, 9),
      ...gopuram(415, GROUND, 355, 220, 9),
      ...gopuram(630, GROUND, 340, 211, 9),
      ...gopuram(845, GROUND, 320, 198, 9),
    ],
    fore: wall(GROUND, 52),
  },
  {
    id: "rameswaram",
    city: "Rameswaram",
    ta: "ராமேஸ்வரம்",
    monument: "Pamban bridge",
    economy: "Fisheries, pilgrimage",
    far: [...gopuram(760, GROUND - 70, 210, 130, 9)],
    mid: pamban(GROUND, 96),
    fore: [],
  },
  {
    id: "kanyakumari",
    city: "Kanyakumari",
    ta: "கன்னியாகுமரி",
    monument: "Vivekananda Rock · Thiruvalluvar",
    economy: "Wind energy, fisheries",
    far: [],
    // a horizontal block, a gap of sea, a human figure — reads at any size
    mid: [
      rect(300, GROUND - 74, 190, 74),
      poly([
        [300, GROUND - 74],
        [345, GROUND - 116],
        [445, GROUND - 116],
        [490, GROUND - 74],
      ]),
      rect(388, GROUND - 150, 14, 36),
    ],
    fore: [
      // the statue: a standing figure, deliberately simple
      rect(690, GROUND - 62, 46, 62),
      rect(700, GROUND - 190, 26, 130),
      poly([
        [700, GROUND - 190],
        [713, GROUND - 214],
        [726, GROUND - 190],
      ]),
    ],
  },
];
