/* The journey — a camera flying west across Tamil Nadu.
 *
 * Five landscapes, each scaling past the viewer as you scroll, reversing
 * exactly when you scroll back. Ordered east → west so three things move
 * together: the horizon rises, the light runs dawn → dusk, and the economy
 * goes from port and IT to agriculture — the axis this platform exists to
 * bridge. See monuments-north.md §1 for why that ordering was chosen.
 */

import ZoomStory, { type ZoomScene } from "./ZoomStory";
import { STOPS } from "./monuments";

/** What each stop says. Tied to founders, not to tourism. */
const COPY: Record<string, { title: string; lede: string }> = {
  Chennai: {
    title: "Every founder\nstarts somewhere",
    lede: "The port, the auto belt, the IT corridor. Where the capital already is.",
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
    title: "Some build where\nno one is looking",
    lede: "Leather, hospitals, engineering campuses — an industrial district, inland.",
  },
  Tiruvannamalai: {
    title: "The map does not\nend at the city",
    lede: "Agriculture, handloom, a pilgrim economy. Furthest from the port, counted the same.",
  },
};

export default function Journey() {
  const scenes: ZoomScene[] = STOPS.map((stop) => {
    const Backdrop = stop.backdrop;
    const copy = COPY[stop.place];
    return {
      id: stop.n,
      n: stop.n,
      place: stop.place,
      placeTa: stop.placeTa,
      title: copy.title,
      lede: copy.lede,
      meta: stop.caption,
      layers: <Backdrop />,
    };
  });

  return <ZoomStory scenes={scenes} screensPerScene={1.6} />;
}
