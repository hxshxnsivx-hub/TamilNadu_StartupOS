// Mirrors the backend CompletenessScorer (app/services/completeness.py) so the
// meter is accurate offline. When the /profiles endpoint lands, this is replaced
// by the server's authoritative score.

export interface Founder {
  name?: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  state?: string;
  district?: string;
  city?: string;
  highest_qualification?: string;
  institution?: string;
  graduation_year?: string;
  first_graduate?: boolean;
  caste_category?: string;
}
export interface Startup {
  startup_name?: string;
  entity_type?: string;
  domain?: string;
  stage?: string;
}
export interface ProfileDraft {
  founder: Founder;
  startup: Startup;
  docsVerified: boolean;
}

const BASIC = ["name", "email", "phone", "date_of_birth", "gender", "state", "district", "city"];
const EDUCATION = ["highest_qualification", "institution", "graduation_year"];
const STARTUP = ["startup_name", "entity_type", "domain", "stage"];

const TIER_LABEL: Record<number, string> = {
  0: "incomplete",
  40: "basic",
  60: "standard",
  80: "verified",
  100: "investment_ready",
};

function missingFrom(obj: object, keys: string[]): string[] {
  const rec = obj as Record<string, unknown>;
  return keys.filter((k) => {
    const v = rec?.[k];
    return v === undefined || v === null || v === "";
  });
}

export interface Score {
  score: number;
  tier: string;
  missing: string[];
}

export function scoreProfile(p: ProfileDraft): Score {
  const basicMiss = missingFrom(p.founder, BASIC);
  const eduMiss = missingFrom(p.founder, EDUCATION);
  const startupMiss = missingFrom(p.startup, STARTUP);

  const basicOk = basicMiss.length === 0;
  const eduOk = basicOk && eduMiss.length === 0;
  const startupOk = eduOk && startupMiss.length === 0;
  const docsOk = startupOk && p.docsVerified;

  let score = 0;
  if (basicOk) score = 40;
  if (eduOk) score = 60;
  if (startupOk) score = 80;
  if (docsOk) score = 100;

  let missing: string[] = [];
  if (!basicOk) missing = basicMiss.map((f) => `founder.${f}`);
  else if (!eduOk) missing = eduMiss.map((f) => `founder.${f}`);
  else if (!startupOk) missing = startupMiss.map((f) => `startup.${f}`);
  else if (!docsOk) missing = ["documents.verified"];

  return { score, tier: TIER_LABEL[score], missing };
}
