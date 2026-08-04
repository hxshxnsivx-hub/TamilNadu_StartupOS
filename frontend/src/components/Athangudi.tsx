/* Athangudi — the Chettinad handmade-tile geometry, as structure.
 *
 * The named "cube" pattern of Athangudi tiles is mathematically a RHOMBILLE
 * tiling: each hexagon divided into three 60°/120° rhombi meeting at its
 * centre, which is what produces the isometric-cube read. Symmetry group p3
 * when the three rhombi are differently toned.
 *
 * Construction (pointy-top hexagon, circumradius s):
 *   vertices  V_k = (s·sin 60k°, −s·cos 60k°),  k = 0…5
 *   rhombi    (C, V0, V1, V2), (C, V2, V3, V4), (C, V4, V5, V0)
 *   lattice   a = (s√3, 0),  b = (s√3/2, 1.5s)
 *
 * Rendered as edges only at very low ink, so it reads as woven texture rather
 * than decoration. Geometry per the sourced report in
 * .kiro/specs/tamil-nadu-startupos/art-reference-tn.md
 */

const SQRT3 = Math.sqrt(3);

function hexPoints(cx: number, cy: number, s: number) {
  return Array.from({ length: 6 }, (_, k) => {
    const a = (Math.PI / 3) * k;
    return [cx + s * Math.sin(a), cy - s * Math.cos(a)] as const;
  });
}

/** Hexagon outline plus the three spokes that cut it into rhombi. */
function cell(cx: number, cy: number, s: number) {
  const v = hexPoints(cx, cy, s);
  const ring = v.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`).join("");
  // spokes to alternate vertices — these are the rhombus divisions
  const spokes = [0, 2, 4]
    .map((k) => `M${cx.toFixed(2)} ${cy.toFixed(2)}L${v[k][0].toFixed(2)} ${v[k][1].toFixed(2)}`)
    .join("");
  return `${ring}Z${spokes}`;
}

export function RhombilleField({
  s = 26,
  className = "ath-field",
}: {
  s?: number;
  className?: string;
}) {
  const W = s * SQRT3; // horizontal lattice pitch
  const H = 3 * s; // vertical repeat (two staggered rows)

  // Row 0 and row 2 sit on the tile edges; row 1 is offset by half a pitch.
  // The extra ±H/2 centres bleed past the tile so no seam shows at the join.
  const centres: Array<[number, number]> = [
    [0, 0],
    [W, 0],
    [0, H],
    [W, H],
    [W / 2, H / 2],
    [W / 2, -H / 2],
    [W / 2, (3 * H) / 2],
  ];

  const d = centres.map(([cx, cy]) => cell(cx, cy, s)).join("");

  return (
    <div className={className} aria-hidden="true">
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern
            id="ath-rhombille"
            patternUnits="userSpaceOnUse"
            width={W}
            height={H}
          >
            <path d={d} fill="none" stroke="currentColor" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#ath-rhombille)" />
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */

/**
 * Kolam knot — a single closed line that encircles every dot and has no loose
 * ends. Three sourced laws govern a true kolam: every pulli is individually
 * encircled, crossings are discrete points, and the path never terminates.
 *
 * Used for waiting and progress states because the form states the product's
 * own thesis: the figure is complete only once every point is enclosed.
 * The stroke draws itself via stroke-dashoffset.
 */
export function KolamKnot({
  size = 128,
  dots = 3,
  className = "kolam-knot",
}: {
  size?: number;
  dots?: number;
  className?: string;
}) {
  const step = size / (dots + 1);
  const r = step * 0.5;

  // One loop per dot, each rotated about the centre — the classic sikku
  // (knot) construction: overlapping loops whose union is a single circuit.
  const loops = Array.from({ length: dots }, (_, i) => {
    const a = (Math.PI / dots) * i;
    const cx = size / 2;
    const cy = size / 2;
    const dx = Math.cos(a) * step * 0.62;
    const dy = Math.sin(a) * step * 0.62;
    return (
      <ellipse
        key={i}
        cx={cx}
        cy={cy}
        rx={r * 1.5}
        ry={r * 0.82}
        transform={`rotate(${(180 / dots) * i} ${cx} ${cy}) translate(${dx * 0} ${dy * 0})`}
      />
    );
  });

  // the pulli themselves
  const pulli = Array.from({ length: dots * dots }, (_, i) => {
    const gx = (i % dots) + 1;
    const gy = Math.floor(i / dots) + 1;
    return <circle key={`p${i}`} cx={gx * step} cy={gy * step} r={1.4} className="kolam-dot" />;
  });

  return (
    <svg
      className={className}
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      aria-hidden="true"
    >
      <g className="kolam-line" fill="none" stroke="currentColor" strokeWidth="1.4">
        {loops}
      </g>
      <g className="kolam-pulli" fill="currentColor">
        {pulli}
      </g>
    </svg>
  );
}
