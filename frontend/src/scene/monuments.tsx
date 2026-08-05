/* Monument backdrops.
 *
 * Every scene is built from the same five planes so depth reads consistently:
 *   0 sky · 1 sun · 2 far ridge · 3 THE MONUMENT · 4 foreground
 *
 * Silhouettes are drawn, not photographed — no image generation is available
 * here, and drawn silhouettes match the Athangudi / kolam / hara direction the
 * project already uses. They are stylised architectural profiles: no figures,
 * no deities, nothing depicting worship.
 *
 * Geometry: .kiro/specs/tamil-nadu-startupos/monuments-north.md and
 * monuments-south.md. Confidence tags from those documents are carried in the
 * comments — most base widths are [ESTIMATED] because published sources give
 * height and storey count and almost never width.
 */

import { Plane } from "./Scene";
import { gopuramPath, kalasamPositions, type GopuramSpec } from "./gopuram";

const PANEL = "0 0 1200 600";
const GROUND_Y = 548;

/* ---------------------------------------------------------------- sky --- */

/** `warm` runs 0 (dawn, east) → 1 (dusk, west) across the journey. */
export function Sky({ warm = 0.5 }: { warm?: number }) {
  const w = Math.round(warm * 100);
  return (
    <Plane depth={0}>
      <div
        style={{
          background: `linear-gradient(to bottom,
            #0b0a09 0%,
            #171310 20%,
            color-mix(in srgb, #4a3428 ${w}%, #221b17) 50%,
            color-mix(in srgb, #b46a3a ${Math.round(warm * 72)}%, #372a21) 74%,
            color-mix(in srgb, #d9b98a ${Math.round(warm * 62)}%, #4a3428) 90%,
            #0b0a09 100%)`,
        }}
      />
    </Plane>
  );
}

export function Sun({ x = 62, y = 74 }: { x?: number; y?: number }) {
  return (
    <Plane depth={1}>
      <div
        style={{
          background: `radial-gradient(40vmin 40vmin at ${x}% ${y}%, rgba(217,185,138,0.30), transparent 62%),
                       radial-gradient(9vmin 9vmin at ${x}% ${y}%, rgba(247,232,206,0.62), transparent 70%)`,
        }}
      />
    </Plane>
  );
}

/* ------------------------------------------------------------- horizon --- */

/**
 * The far layer. Its amplitude grows across the journey — a flat sea at
 * Chennai, granite domes inland, one 814 m cone at Tiruvannamalai. The land
 * lifting as you scroll is free narrative; it needs no copy.
 */
export function Horizon({ kind }: { kind: "sea" | "plain" | "hills" | "cone" }) {
  const d = {
    sea: `M0 486 L1200 486 L1200 600 L0 600 Z`,
    plain: `M0 478 L300 472 L620 480 L900 470 L1200 478 L1200 600 L0 600 Z`,
    hills: `M0 480 L110 438 L190 462 L300 410 L410 456 L520 430 L660 468
            L790 424 L900 458 L1030 436 L1130 464 L1200 448 L1200 600 L0 600 Z`,
    // Arunachala: one enormous cone, the largest silhouette in the set
    cone: `M0 496 L250 486 L470 470 Q600 214 760 470 L980 480 L1200 492
           L1200 600 L0 600 Z`,
  }[kind];

  return (
    <Plane depth={2}>
      <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
        <path d={d} fill="#131110" />
      </svg>
    </Plane>
  );
}

function Ground() {
  return (
    <Plane depth={4}>
      <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
        <path d={`M0 ${GROUND_Y} L1200 ${GROUND_Y - 18} L1200 600 L0 600 Z`} fill="#0c0a09" />
      </svg>
    </Plane>
  );
}

/* ------------------------------------------------------------- gopuram --- */

export function Gopuram({
  fill = "#1a1715",
  finials = true,
  ...spec
}: GopuramSpec & { fill?: string }) {
  const pots = finials ? kalasamPositions(spec) : [];
  return (
    <g fill={fill}>
      <path d={gopuramPath(spec)} />
      {pots.map((p, i) => (
        <g key={i}>
          <rect x={p.x - p.r * 0.34} y={p.y - p.stem} width={p.r * 0.68} height={p.stem} />
          <circle cx={p.x} cy={p.y - p.stem} r={p.r} />
        </g>
      ))}
    </g>
  );
}

/* -------------------------------------------------------------- scenes --- */

/** Chennai — sea horizon, dead flat. Lighthouse + Napier bridge deck. */
function ChennaiScene() {
  return (
    <>
      <Sky warm={0.18} />
      <Sun x={78} y={78} />
      <Horizon kind="sea" />
      <Plane depth={3}>
        <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
          {/* Kapaleeshwarar gopuram, Mylapore — base width [ESTIMATED] */}
          <Gopuram cx={280} baseY={GROUND_Y} H={330} W={150} tiers={7} fill="#191614" />
          {/* the round lighthouse: a plain cylinder with a lamp gallery */}
          <g fill="#151312">
            <rect x={905} y={GROUND_Y - 250} width={34} height={250} />
            <rect x={896} y={GROUND_Y - 268} width={52} height={20} />
            <rect x={912} y={GROUND_Y - 290} width={20} height={24} />
          </g>
          {/* Napier bridge deck — a low horizontal, arches beneath */}
          <g fill="#100e0d">
            <rect x={520} y={GROUND_Y - 62} width={640} height={12} />
            {[0, 1, 2, 3, 4].map((i) => (
              <path
                key={i}
                d={`M${540 + i * 126} ${GROUND_Y - 50} q63 -42 126 0 Z`}
                fill="none"
                stroke="#100e0d"
                strokeWidth="7"
              />
            ))}
          </g>
        </svg>
      </Plane>
      <Ground />
    </>
  );
}

/** Mahabalipuram — Shore Temple, two vimanas of unequal height, on the sand. */
function MahabalipuramScene() {
  return (
    <>
      <Sky warm={0.32} />
      <Sun x={70} y={76} />
      <Horizon kind="sea" />
      <Plane depth={3}>
        <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
          {/* Pallava vimana: a stepped pyramid, steeper and smaller than a
              gopuram, crowned by an octagonal śikhara rather than a barrel
              vault. The taller eastern tower and its shorter western twin. */}
          <Gopuram cx={640} baseY={GROUND_Y} H={300} W={116} tiers={5} fill="#1b1816" />
          <Gopuram cx={510} baseY={GROUND_Y} H={196} W={92} tiers={4} fill="#171412" />
          {/* compound wall with its row of seated bull finials, abstracted to
              plain merlons — no animal or figure is drawn */}
          <g fill="#121010">
            <rect x={400} y={GROUND_Y - 46} width={360} height={46} />
            {Array.from({ length: 13 }, (_, i) => (
              <rect key={i} x={406 + i * 28} y={GROUND_Y - 60} width={15} height={16} />
            ))}
          </g>
        </svg>
      </Plane>
      <Ground />
    </>
  );
}

/** Kanchipuram — the Ekambareswarar rajagopuram, a silk-town skyline. */
function KanchipuramScene() {
  return (
    <>
      <Sky warm={0.48} />
      <Sun x={62} y={74} />
      <Horizon kind="plain" />
      <Plane depth={3}>
        <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
          <Gopuram cx={620} baseY={GROUND_Y} H={430} W={250} tiers={11} fill="#1c1917" />
          <Gopuram cx={300} baseY={GROUND_Y} H={214} W={116} tiers={5} fill="#151312" />
          <Gopuram cx={930} baseY={GROUND_Y} H={186} W={104} tiers={5} fill="#141211" />
          <rect x={0} y={GROUND_Y - 34} width={1200} height={34} fill="#0f0d0c" />
        </svg>
      </Plane>
      <Ground />
    </>
  );
}

/** Vellore — the fort: ramparts and a moat, a gopuram rising from inside it. */
function VelloreScene() {
  return (
    <>
      <Sky warm={0.66} />
      <Sun x={44} y={72} />
      <Horizon kind="hills" />
      <Plane depth={3}>
        <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
          {/* Jalakandeswarar gopuram, standing above the walls */}
          <Gopuram cx={640} baseY={GROUND_Y - 70} H={260} W={130} tiers={7} fill="#1b1816" />
          {/* rampart with round bastions — the fort's distinguishing profile */}
          <g fill="#131110">
            <rect x={60} y={GROUND_Y - 76} width={1080} height={76} />
            {[150, 470, 800, 1090].map((x) => (
              <g key={x}>
                <rect x={x - 46} y={GROUND_Y - 104} width={92} height={104} />
                <path d={`M${x - 46} ${GROUND_Y - 104} h92 v-10 h-92 Z`} />
              </g>
            ))}
            {/* merlons along the curtain wall */}
            {Array.from({ length: 34 }, (_, i) => (
              <rect key={i} x={70 + i * 32} y={GROUND_Y - 88} width={16} height={14} />
            ))}
          </g>
        </svg>
      </Plane>
      <Ground />
    </>
  );
}

/** Tiruvannamalai — Arunachala. The largest silhouette; it must come last. */
function TiruvannamalaiScene() {
  return (
    <>
      <Sky warm={0.9} />
      <Sun x={26} y={70} />
      <Horizon kind="cone" />
      <Plane depth={3}>
        <svg viewBox={PANEL} preserveAspectRatio="xMidYMax slice">
          {/* the Annamalaiyar rajagopuram sits small against the mountain —
              that contrast is the whole point of the panel */}
          <Gopuram cx={330} baseY={GROUND_Y} H={352} W={168} tiers={11} fill="#1a1715" />
          <rect x={0} y={GROUND_Y - 40} width={1200} height={40} fill="#0f0d0c" />
        </svg>
      </Plane>
      <Ground />
    </>
  );
}

/* ------------------------------------------------------------ registry --- */

export type Stop = {
  n: string;
  place: string;
  placeTa: string;
  caption: string;
  backdrop: () => JSX.Element;
};

/**
 * East → west, coast to hills. Three things move together across the run:
 * the horizon rises, the light goes from dawn to dusk, and the economy runs
 * from port and IT to agriculture — the axis this platform exists to bridge.
 *
 * Captions are [ESTIMATED] regional associations, not figures from an
 * industrial survey. Verify before presenting them as claims.
 */
export const STOPS: Stop[] = [
  {
    n: "01",
    place: "Chennai",
    placeTa: "சென்னை",
    caption: "auto · IT · ports · fintech",
    backdrop: ChennaiScene,
  },
  {
    n: "02",
    place: "Mahabalipuram",
    placeTa: "மாமல்லபுரம்",
    caption: "coastal tourism · sculpture · OMR corridor",
    backdrop: MahabalipuramScene,
  },
  {
    n: "03",
    place: "Kanchipuram",
    placeTa: "காஞ்சிபுரம்",
    caption: "silk weaving · temple economy",
    backdrop: KanchipuramScene,
  },
  {
    n: "04",
    place: "Vellore",
    placeTa: "வேலூர்",
    caption: "leather · healthcare · engineering campuses",
    backdrop: VelloreScene,
  },
  {
    n: "05",
    place: "Tiruvannamalai",
    placeTa: "திருவண்ணாமலை",
    caption: "pilgrim economy · agri · handloom",
    backdrop: TiruvannamalaiScene,
  },
];
