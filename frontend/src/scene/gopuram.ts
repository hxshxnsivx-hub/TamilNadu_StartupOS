/* Parametric gopuram generator.
 *
 * Implements the construction algorithm in
 * .kiro/specs/tamil-nadu-startupos/monuments-north.md §0.3, calibrated against
 * the one tower in the research with BOTH base and top dimensions published —
 * Srirangam's Rajagopuram, 50.6 m → 29.9 m across 13 tiers, a measured
 * per-tier factor of 0.9603 on the wide face.
 *
 * Three things make this read as a gopuram rather than a generic pyramid, and
 * all three are easy to leave out:
 *   1. a VERTICAL base block carrying the battered superstructure
 *   2. a KAPOTA LIP flaring at each tier top — this is what serrates the edge
 *   3. a transverse barrel-vaulted ŚĀLA crown, not a point
 *
 * Confidence, carried from the research: the taper is [DERIVED] from sourced
 * dimensions; base_h, W_top and the kalasam counts are [ESTIMATED]. Published
 * sources give total height and storey count and almost never base width, so
 * these are honest plausible proportions, not a measured elevation.
 */

export type GopuramSpec = {
  /** centre x in panel units */
  cx: number;
  /** ground line y */
  baseY: number;
  /** total height including finials */
  H: number;
  /** base width */
  W: number;
  /** number of talas (storeys) */
  tiers: number;
  /** drop finials at far-layer scale — they alias to fuzz */
  finials?: boolean;
};

const BASE_FRAC = 0.2; // [ESTIMATED] 0.16–0.24
const SUPER_FRAC = 0.74; // [ESTIMATED]
/* [DERIVED, measured] Srirangam is the only tower in the research with both
   base and top published: 29.9 / 50.6 = 0.591 on the wide face. The research's
   own [ESTIMATED] range was 0.45–0.55, which the one real measurement sits
   outside — so the measurement wins. At 0.50 the towers render noticeably too
   pointy for a South Indian gopuram. */
const TOP_FRAC = 0.591;
const BATTER_P = 1.18; // [ESTIMATED] >1 bows the sides inward
const LIP_OUT = 0.03; // kapota flare, as a fraction of W
const LIP_H = 0.35; // as a fraction of tier height
const TIER_H_RATIO = 0.93; // tier heights shrink slower than widths

/** Odd finial count by tower size. [ESTIMATED — a drawing convention.] */
function kalasamCount(tiers: number): number {
  if (tiers <= 7) return 5;
  if (tiers <= 10) return 9;
  return 13;
}

/** Solve h0 so the geometric run of tier heights sums to the superstructure. */
function firstTierHeight(superH: number, tiers: number): number {
  let sum = 0;
  for (let i = 0; i < tiers; i++) sum += Math.pow(TIER_H_RATIO, i);
  return superH / sum;
}

/**
 * Returns an SVG path for the tower's outline plus its lips, as one `d`.
 * A single path keeps the silhouette one filled shape — no seams show when
 * it is drawn in a flat colour against the sky.
 */
export function gopuramPath(spec: GopuramSpec): string {
  const { cx, baseY, H, W, tiers } = spec;
  const baseH = BASE_FRAC * H;
  const superH = SUPER_FRAC * H;
  const wTop = TOP_FRAC * W;
  const h0 = firstTierHeight(superH, tiers);

  const widthAt = (t: number) => wTop + (W - wTop) * Math.pow(1 - t, BATTER_P);

  // Walk UP the left side collecting points, then mirror down the right.
  const left: Array<[number, number]> = [];
  const right: Array<[number, number]> = [];

  // 1. vertical base block
  let y = baseY;
  left.push([cx - W / 2, y]);
  right.push([cx + W / 2, y]);
  y -= baseH;
  left.push([cx - W / 2, y]);
  right.push([cx + W / 2, y]);

  // 2. battered superstructure, tier by tier
  for (let i = 0; i < tiers; i++) {
    const t0 = tiers === 1 ? 0 : i / (tiers - 1);
    const t1 = tiers === 1 ? 1 : (i + 1) / (tiers - 1);
    const w0 = widthAt(t0);
    const w1 = widthAt(Math.min(1, t1));
    const hi = h0 * Math.pow(TIER_H_RATIO, i);

    // trapezoid body: w0 at the bottom, narrowing to w1
    const bodyTop = y - hi * (1 - LIP_H);
    left.push([cx - w0 / 2, y]);
    right.push([cx + w0 / 2, y]);
    left.push([cx - w1 / 2, bodyTop]);
    right.push([cx + w1 / 2, bodyTop]);

    // kapota lip — flares OUT past the tier above, serrating the edge
    const lip = w1 / 2 + LIP_OUT * W;
    left.push([cx - lip, bodyTop]);
    right.push([cx + lip, bodyTop]);
    y = bodyTop - hi * LIP_H;
    left.push([cx - lip, y]);
    right.push([cx + lip, y]);
    left.push([cx - w1 / 2, y]);
    right.push([cx + w1 / 2, y]);
  }

  // 3. śāla — vertical sides, then a semi-ellipse over the top
  const salaW = 1.15 * wTop;
  const salaH = 0.06 * H;
  const salaBase = y;
  const salaShoulder = y - salaH * 0.35;
  left.push([cx - salaW / 2, salaBase]);
  right.push([cx + salaW / 2, salaBase]);
  left.push([cx - salaW / 2, salaShoulder]);
  right.push([cx + salaW / 2, salaShoulder]);

  const rx = salaW / 2;
  const ry = 0.65 * salaH;

  const fmt = ([x, yy]: [number, number]) => `${x.toFixed(1)} ${yy.toFixed(1)}`;

  // up the left side, arc over the vault, back down the right side, close.
  // `right` already ends at the right shoulder, which the arc reaches, so it
  // is dropped before walking back down.
  const upLeft = left.map(fmt);
  const downRight = right.slice(0, -1).reverse().map(fmt);

  return [
    `M${upLeft[0]}`,
    ...upLeft.slice(1).map((p) => `L${p}`),
    `A${rx.toFixed(1)} ${ry.toFixed(1)} 0 0 1 ${fmt([cx + salaW / 2, salaShoulder])}`,
    ...downRight.map((p) => `L${p}`),
    "Z",
  ].join("");
}

/** Where the finials sit, so the caller can draw them as separate marks. */
export function kalasamPositions(spec: GopuramSpec) {
  const { cx, baseY, H, W, tiers } = spec;
  const baseH = BASE_FRAC * H;
  const superH = SUPER_FRAC * H;
  const wTop = TOP_FRAC * W;
  const salaW = 1.15 * wTop;
  const salaH = 0.06 * H;
  const ridgeY = baseY - baseH - superH - salaH * 0.35 - 0.65 * salaH;

  const n = kalasamCount(tiers);
  const stem = 0.03 * H;
  const r = 0.018 * W;

  return Array.from({ length: n }, (_, i) => {
    const f = n === 1 ? 0 : i / (n - 1) - 0.5; // -0.5 … +0.5
    // tallest at the centre, tapering to the ends
    const scale = 1 - Math.abs(f) * 1.1;
    return {
      x: cx + f * salaW * 0.86,
      y: ridgeY,
      stem: stem * Math.max(0.45, scale),
      r: r * Math.max(0.55, scale),
    };
  });
}

/** Per-tier width factors, for reference/tests. Srirangam measures 0.9603. */
export function taperFactors(tiers: number): number[] {
  const wTop = TOP_FRAC;
  const out: number[] = [];
  for (let i = 0; i < tiers; i++) {
    const t = tiers === 1 ? 0 : i / (tiers - 1);
    out.push(wTop + (1 - wTop) * Math.pow(1 - t, BATTER_P));
  }
  return out;
}
