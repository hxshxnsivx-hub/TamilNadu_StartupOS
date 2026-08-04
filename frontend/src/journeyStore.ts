/* The founder's route through the product, held in the browser.
 *
 * Two enums set at the front door decide what every downstream screen shows,
 * so they live in one place rather than being re-asked per page:
 *
 *   entry_mode   how the founder arrived — with an idea, with a domain, or
 *                with nothing but the intention to start
 *   reg_subtype  what already exists legally — a registered company with a
 *                product, registered without one, an idea-worker with no
 *                company, or nothing registered at all
 *
 * `terrain` is auto-classified from those two and is deliberately
 * FOUNDER-OVERRIDABLE. A classifier that cannot be argued with is a
 * classifier that quietly mis-serves the people it gets wrong.
 *
 * Nothing here is sent anywhere. It is a draft the founder holds, in the same
 * spirit as profileStore, and it is versioned so a shape change cannot
 * resurrect a stale record as though it were current.
 */

const KEY = "vanigam_journey";
const VERSION = 1;

export type EntryMode = "idea" | "domain_only" | "intent_only";
export type RegSubtype =
  | "registered_with_product"
  | "registered_no_product"
  | "idea_worker_no_company"
  | "unregistered";
export type Terrain = "urban_tech" | "rural_micro" | "academic_spinoff" | "deep_tech";

export type MilestoneStatus = "pending" | "in_progress" | "done";

export interface MilestoneRecord {
  status: MilestoneStatus;
  notes: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Journey {
  version: number;
  entry_mode: EntryMode | null;
  reg_subtype: RegSubtype | null;
  terrain: Terrain | null;
  /** true once the founder has accepted or changed the auto-classification */
  terrain_confirmed: boolean;
  /** DPDP consent, one flag per purpose — never one blanket "I agree" */
  consent: Record<string, boolean>;
  /** milestone id → tracking record */
  milestones: Record<string, MilestoneRecord>;
}

export const EMPTY: Journey = {
  version: VERSION,
  entry_mode: null,
  reg_subtype: null,
  terrain: null,
  terrain_confirmed: false,
  consent: {},
  milestones: {},
};

export function loadJourney(): Journey {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...EMPTY };
    const j = JSON.parse(raw) as Partial<Journey>;
    // A record written by an older shape is discarded rather than merged.
    // Half-migrated state is worse than a clean restart, because the founder
    // cannot see which half is stale.
    if (j.version !== VERSION) return { ...EMPTY };
    return { ...EMPTY, ...j };
  } catch {
    return { ...EMPTY };
  }
}

export function saveJourney(j: Journey) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...j, version: VERSION }));
  } catch {
    /* private mode, quota, or storage disabled — the session still works,
       it just will not be remembered. Never let this break a render. */
  }
}

/**
 * Auto-classify terrain from the two entry enums.
 *
 * This is a first guess presented for confirmation, never a verdict. The
 * mapping is deliberately coarse: a founder who is wrongly read as rural_micro
 * loses nothing but one click, whereas a confident mis-classification that
 * could not be overridden would quietly route them past the schemes they are
 * actually eligible for.
 */
export function classifyTerrain(
  mode: EntryMode | null,
  sub: RegSubtype | null,
): Terrain | null {
  if (!mode || !sub) return null;
  if (sub === "registered_with_product" && mode === "idea") return "deep_tech";
  if (sub === "registered_with_product") return "urban_tech";
  if (sub === "idea_worker_no_company") return "academic_spinoff";
  if (sub === "unregistered" && mode === "intent_only") return "rural_micro";
  if (mode === "domain_only") return "rural_micro";
  return "urban_tech";
}

/* ---- copy for the two questions, kept beside the enums they set ---- */

export const ENTRY_MODES: Array<{
  id: EntryMode;
  label: string;
  ta: string;
  body: string;
}> = [
  {
    id: "idea",
    label: "I have an idea",
    ta: "என்னிடம் ஒரு யோசனை உள்ளது",
    body: "You can describe what you want to build, even roughly. We start by testing whether it holds up.",
  },
  {
    id: "domain_only",
    label: "I know my field, not my idea",
    ta: "துறை தெரியும், யோசனை இல்லை",
    body: "You know the trade or sector you want to work in. We start from the problems that field actually has.",
  },
  {
    id: "intent_only",
    label: "I only know I want to start",
    ta: "தொடங்க வேண்டும் — அவ்வளவுதான்",
    body: "No idea and no field yet. We start from what you already know how to do.",
  },
];

export const REG_SUBTYPES: Array<{
  id: RegSubtype;
  label: string;
  ta: string;
  body: string;
}> = [
  {
    id: "registered_with_product",
    label: "Registered, with a product",
    ta: "பதிவு செய்யப்பட்டது · தயாரிப்பு உள்ளது",
    body: "A company exists and it sells or ships something.",
  },
  {
    id: "registered_no_product",
    label: "Registered, no product yet",
    ta: "பதிவு செய்யப்பட்டது · தயாரிப்பு இல்லை",
    body: "The entity exists on paper; nothing has shipped.",
  },
  {
    id: "idea_worker_no_company",
    label: "Working on it, no company",
    ta: "வேலை நடக்கிறது · நிறுவனம் இல்லை",
    body: "You are building or researching, possibly inside a college or a job.",
  },
  {
    id: "unregistered",
    label: "Nothing registered",
    ta: "எதுவும் பதிவு இல்லை",
    body: "Nothing legal exists yet. That is the most common place to start.",
  },
];

export const TERRAINS: Array<{ id: Terrain; label: string; body: string }> = [
  {
    id: "urban_tech",
    label: "Urban tech",
    body: "City-based, software or platform-led, competing for the usual startup schemes.",
  },
  {
    id: "rural_micro",
    label: "Rural / micro-enterprise",
    body: "District-based, small capital, often trade or manufacturing. Different schemes entirely.",
  },
  {
    id: "academic_spinoff",
    label: "Academic spin-off",
    body: "Out of a college, lab or research group. Opens student and incubation routes.",
  },
  {
    id: "deep_tech",
    label: "Deep tech",
    body: "Hardware, materials, biotech or long-R&D. Longer timelines, specific grant tracks.",
  },
];
