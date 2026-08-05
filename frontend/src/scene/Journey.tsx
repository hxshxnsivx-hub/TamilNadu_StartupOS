/* The journey — five cinematic scenes, coast to hills.
 *
 * Each stop pins for two screens while its monument drifts in parallax behind
 * the chapter copy, then hands over to the next. Reading east → west means the
 * horizon rises, the light runs dawn → dusk, and the economy moves from port
 * and IT to agriculture. That last one is the platform's own thesis, argued by
 * the background without a line of copy.
 */

import { Scene } from "./Scene";
import { STOPS } from "./monuments";

/** What each stop says, tied to the platform rather than to tourism. */
const COPY: Record<string, { title: string; lede: string }> = {
  Chennai: {
    title: "Every founder\nstarts somewhere",
    lede: "The port, the auto belt, the IT corridor. Where capital already is.",
  },
  Mahabalipuram: {
    title: "Some start\nwith a craft",
    lede: "Stone cut for thirteen centuries, and a coastline of small enterprise.",
  },
  Kanchipuram: {
    title: "Some inherit\na trade",
    lede: "A silk economy older than any company, still run family by family.",
  },
  Vellore: {
    title: "Some build\nwhere no one looks",
    lede: "Leather, hospitals, engineering campuses — an industrial district, inland.",
  },
  Tiruvannamalai: {
    title: "The map does not\nend at the city",
    lede: "Agriculture, handloom, a pilgrim economy. Furthest from the port, and counted the same.",
  },
};

export default function Journey() {
  return (
    <div className="sc-journey">
      {STOPS.map((stop) => {
        const Backdrop = stop.backdrop;
        const copy = COPY[stop.place];
        return (
          <Scene
            key={stop.n}
            n={stop.n}
            place={stop.place}
            placeTa={stop.placeTa}
            title={copy.title}
            lede={copy.lede}
            body={stop.caption}
            backdrop={<Backdrop />}
            screens={2}
          />
        );
      })}
    </div>
  );
}
