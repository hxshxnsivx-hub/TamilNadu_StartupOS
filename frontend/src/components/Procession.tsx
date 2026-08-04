/* The procession — the mural cast walking a kolam curve across the page.
   Built on MarqueeAlongSvgPath, dressed in the project's own material:
   the four figures and their Tamil names, on gilded medallions, following
   the sweeping loop a kolam line actually takes. */

import MarqueeAlongSvgPath from "@/components/ui/marquee-along-svg-path";
import { Sower, Trader, Treasurer, Weaver } from "./Mural";

// A kolam sweep: out, over, back under, and away — one continuous stroke.
const KOLAM_PATH =
  "M1 209.434C58.5872 255.935 387.926 325.938 482.583 209.434C600.905 63.8051 525.516 -43.2211 427.332 19.9613C329.149 83.1436 352.902 242.723 515.041 267.302C644.752 286.966 943.56 181.94 995 156.5";

const CAST = [
  { Figure: Sower, name: "விதைப்பவர்", tone: "var(--jade)" },
  { Figure: Weaver, name: "நெசவாளர்", tone: "var(--indigo)" },
  { Figure: Trader, name: "வணிகன்", tone: "var(--madder)" },
  { Figure: Treasurer, name: "கணக்கன்", tone: "var(--ochre)" },
];

export default function Procession() {
  return (
    <div className="mq-band">
      <MarqueeAlongSvgPath
        path={KOLAM_PATH}
        viewBox="0 0 996 330"
        baseVelocity={6}
        repeat={2}
        slowdownOnHover
        slowDownFactor={0.22}
        draggable
        dragSensitivity={0.1}
        grabCursor
        showPath
        responsive
        className="mq-full"
        cssVariableInterpolation={[{ property: "opacity", from: 0.35, to: 1 }]}
      >
        {CAST.flatMap(({ Figure, name, tone }) => [
          <div className="mq-fig" key={`${name}-f`}>
            <Figure tone={tone} />
          </div>,
          <div className="mq-word" key={`${name}-w`}>
            {name}
          </div>,
        ])}
      </MarqueeAlongSvgPath>
    </div>
  );
}
