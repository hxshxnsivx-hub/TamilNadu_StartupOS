/* Tamil Nadu mural cast — the four figures who carry the founder's story.
   Drawn in the Thanjavur/Chola idiom: almond eyes, ornate crowns, jewelled
   collars, gold contour over jewel ground. Flat vector, no gradients inside
   the figures themselves, so they stay legible at any size and never read as
   clip-art. Each figure carries the attribute of its chapter. */

type FigureProps = { className?: string; tone?: string };

/** Shared scaffolding: halo, crown, face, collar — the mural "grammar". */
function Body({
  tone = "var(--ochre)",
  children,
}: {
  tone?: string;
  children?: React.ReactNode;
}) {
  return (
    <>
      {/* halo — the arc every mural figure is seated within */}
      <circle cx="60" cy="52" r="34" fill={tone} opacity="0.14" />
      <circle
        cx="60"
        cy="52"
        r="34"
        fill="none"
        stroke="var(--ochre)"
        strokeWidth="0.9"
        opacity="0.55"
      />

      {/* crown / kirīṭam */}
      <path
        d="M42 30c4-11 10-17 18-17s14 6 18 17c-6-4-12-6-18-6s-12 2-18 6z"
        fill={tone}
        opacity="0.85"
      />
      <path
        d="M42 30c4-11 10-17 18-17s14 6 18 17"
        fill="none"
        stroke="var(--gold-pale)"
        strokeWidth="1.1"
        strokeLinecap="round"
      />
      <circle cx="60" cy="16" r="2.6" fill="var(--gold-pale)" />

      {/* face */}
      <ellipse cx="60" cy="46" rx="15" ry="17" fill="var(--carbon-3)" />
      <ellipse
        cx="60"
        cy="46"
        rx="15"
        ry="17"
        fill="none"
        stroke="var(--ochre)"
        strokeWidth="1.1"
      />
      {/* almond eyes — the signature of the idiom */}
      <path
        d="M50 44c2.6-3.4 7-3.4 9.6 0-2.6 3.4-7 3.4-9.6 0z"
        fill="var(--chalk)"
      />
      <path
        d="M60.4 44c2.6-3.4 7-3.4 9.6 0-2.6 3.4-7 3.4-9.6 0z"
        fill="var(--chalk)"
      />
      <circle cx="54.6" cy="44" r="1.7" fill="var(--carbon)" />
      <circle cx="65.2" cy="44" r="1.7" fill="var(--carbon)" />
      {/* brow + tilaka */}
      <path
        d="M49 39.5c3-2.2 7.6-2.2 10.6 0M60.4 39.5c3-2.2 7.6-2.2 10.6 0"
        stroke="var(--ochre)"
        strokeWidth="1"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="60" cy="35.5" r="1.5" fill="var(--madder)" />

      {/* jewelled collar + torso */}
      <path
        d="M40 92c2-13 9-21 20-21s18 8 20 21z"
        fill={tone}
        opacity="0.7"
      />
      <path
        d="M40 92c2-13 9-21 20-21s18 8 20 21"
        fill="none"
        stroke="var(--ochre)"
        strokeWidth="1.1"
      />
      <path
        d="M50 76c3.4 4 16.6 4 20 0"
        fill="none"
        stroke="var(--gold-pale)"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <circle cx="60" cy="79" r="2.2" fill="var(--gold-pale)" />
      {children}
    </>
  );
}

/** விதைப்பவர் — the sower. Ideation: a seed held out over open ground. */
export function Sower({ className, tone = "var(--jade)" }: FigureProps) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden="true">
      <Body tone={tone}>
        <path
          d="M28 84c4-7 9-10 14-10"
          stroke="var(--gold-pale)"
          strokeWidth="1.3"
          fill="none"
          strokeLinecap="round"
        />
        <path d="M26 82c-3-4-2-8 2-9 3 4 2 8-2 9z" fill="var(--jade)" />
        <circle cx="21" cy="90" r="1.5" fill="var(--ochre)" opacity="0.8" />
        <circle cx="31" cy="93" r="1.2" fill="var(--ochre)" opacity="0.6" />
      </Body>
    </svg>
  );
}

/** நெசவாளர் — the weaver. Schemes: threads gathered into one cloth. */
export function Weaver({ className, tone = "var(--indigo)" }: FigureProps) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden="true">
      <Body tone={tone}>
        <path
          d="M92 74c-4 0-9 3-13 10"
          stroke="var(--gold-pale)"
          strokeWidth="1.3"
          fill="none"
          strokeLinecap="round"
        />
        <path d="M88 70h14l-3 6H91z" fill="var(--indigo)" />
        <path
          d="M90 78c4 3 9 4 13 3M90 82c4 3 9 4 13 3"
          stroke="var(--ochre)"
          strokeWidth="0.9"
          fill="none"
          opacity="0.75"
        />
      </Body>
    </svg>
  );
}

/** வணிகன் — the trader. B2B: the scale that balances two houses. */
export function Trader({ className, tone = "var(--madder)" }: FigureProps) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden="true">
      <Body tone={tone}>
        <path
          d="M96 66v14M88 74h16"
          stroke="var(--gold-pale)"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
        <path
          d="M88 74l-4 7h8zM104 74l-4 7h8z"
          fill="var(--madder)"
          stroke="var(--ochre)"
          strokeWidth="0.7"
        />
        <circle cx="96" cy="64" r="1.8" fill="var(--gold-pale)" />
      </Body>
    </svg>
  );
}

/** கணக்கன் — the treasurer. Funding: the measured coin. */
export function Treasurer({ className, tone = "var(--ochre)" }: FigureProps) {
  return (
    <svg viewBox="0 0 120 100" className={className} aria-hidden="true">
      <Body tone={tone}>
        <path
          d="M28 76c4 1 8 4 11 9"
          stroke="var(--gold-pale)"
          strokeWidth="1.3"
          fill="none"
          strokeLinecap="round"
        />
        <circle
          cx="24"
          cy="73"
          r="6"
          fill="var(--ochre)"
          stroke="var(--gold-pale)"
          strokeWidth="1"
        />
        <path
          d="M24 69.5v7M21.5 71.5h5"
          stroke="var(--carbon)"
          strokeWidth="1"
          strokeLinecap="round"
        />
      </Body>
    </svg>
  );
}

export const CAST = { Sower, Weaver, Trader, Treasurer };

/** Kolam rail — the domain's own geometry, stepped up the page edge.
    Dots and loops, the way a kolam is actually set out before it is drawn. */
export function KolamRail({ className }: { className?: string }) {
  const rows = [3, 5, 7, 9, 7, 5, 3];
  return (
    <svg viewBox="0 0 60 200" className={className} aria-hidden="true">
      {rows.map((n, r) =>
        Array.from({ length: n }, (_, c) => (
          <circle
            key={`${r}-${c}`}
            cx={30 + (c - (n - 1) / 2) * 9}
            cy={18 + r * 27}
            r="1.6"
            fill="hsl(var(--ambient-1) / 0.5)"
          />
        )),
      )}
      <path
        d="M30 8c14 12 14 34 0 46s-14 34 0 46 14 34 0 46 14 34 0 46"
        fill="none"
        stroke="hsl(var(--ambient-1) / 0.28)"
        strokeWidth="1.1"
      />
    </svg>
  );
}
