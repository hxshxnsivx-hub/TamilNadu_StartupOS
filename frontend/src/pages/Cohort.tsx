/* Cohort: where an idea sits among Tamil Nadu startups, and what a programme's
 * founders have in common.
 *
 * For a founder: similar startups on the Tamil Nadu Startup Map (with the words
 * they share), the sector's registered companies, and plain observations such
 * as "none of them is in Madurai". The page says what the data does not cover.
 *
 * For an incubator: counts across its founders' ideation sessions. Only founders
 * who agreed to share are counted, nothing is shown under 5 of them, and no idea
 * text or name ever appears.
 */

import { useState } from "react";

interface Similar {
  name: string;
  district: string | null;
  sectors: string[];
  tier: string | null;
  stage: string | null;
  about: string;
  shared_words: string[];
  url: string | null;
}

interface Reference {
  similar_startups: Similar[];
  summary: { similar_total: number };
  sector_companies: {
    total: number;
    by_district: Record<string, number>;
    median_year: number | null;
    registered_since_2015: number;
    source: string;
  } | null;
  observations: string[];
  coverage: string;
}

type Counts = Record<string, number>;
interface Programme {
  founders_listed: number;
  founders_sharing: number;
  sessions_found: number;
  shown: boolean;
  reason?: string;
  where_they_are?: Record<string, Counts>;
  their_ideas?: Record<string, Counts>;
  not_worked_out_yet?: Counts;
  progress?: { average_share_of_essentials_known: number; reached_a_roadmap: number };
  privacy?: string;
}

const SECTORS = [
  "agritech", "aerospace_defence", "biotech_pharma", "cleantech", "consumer", "deeptech",
  "edtech", "electronics", "fintech", "food", "healthtech", "hospitality", "logistics",
  "manufacturing", "media", "mobility", "proptech", "saas", "services", "textiles",
];
const DISTRICTS = ["chennai", "coimbatore", "madurai"]; // where the map has startups today
const NAMES: Record<string, string> = {
  saas: "SaaS",
  biotech_pharma: "Biotech and pharma",
  aerospace_defence: "Aerospace and defence",
  edtech: "EdTech",
  fintech: "FinTech",
  healthtech: "HealthTech",
  agritech: "AgriTech",
  proptech: "PropTech",
  deeptech: "Deep tech",
};
const title = (s: string) =>
  NAMES[s] ?? s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.error_message ?? detail.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

function Table({ caption, counts }: { caption: string; counts: Counts }) {
  const rows = Object.entries(counts);
  if (!rows.length) return null;
  return (
    <table>
      <caption>{caption}</caption>
      <tbody>
        {rows.map(([k, n]) => (
          <tr key={k}>
            <th scope="row">{title(k)}</th>
            <td>{n}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ForAnIdea() {
  const [idea, setIdea] = useState("");
  const [sector, setSector] = useState("");
  const [district, setDistrict] = useState("");
  const [out, setOut] = useState<Reference | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setOut(
        await post<Reference>("/api/v1/cohort/reference", {
          idea,
          sector: sector || null,
          district: district || null,
        }),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h2>Your idea among Tamil Nadu startups</h2>
      <form onSubmit={run}>
        <p>
          <label htmlFor="cohort-idea">Describe the idea</label>
          <br />
          <textarea
            id="cohort-idea"
            rows={3}
            cols={70}
            minLength={10}
            required
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
          />
        </p>
        <p>
          <label htmlFor="cohort-sector">Sector</label>{" "}
          <select id="cohort-sector" value={sector} onChange={(e) => setSector(e.target.value)}>
            <option value="">Any</option>
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {title(s)}
              </option>
            ))}
          </select>{" "}
          <label htmlFor="cohort-district">Your district</label>{" "}
          <select id="cohort-district" value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">Not given</option>
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {title(d)}
              </option>
            ))}
          </select>{" "}
          <button type="submit" disabled={busy || idea.trim().length < 10}>
            {busy ? "Looking…" : "Compare"}
          </button>
        </p>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {out ? (
        <>
          <h3>What this shows</h3>
          <ul>
            {out.observations.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
          {out.similar_startups.length ? (
            <>
              <h3>
                Closest startups ({out.similar_startups.length} of {out.summary.similar_total})
              </h3>
              <ol>
                {out.similar_startups.map((s) => (
                  <li key={s.name}>
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {s.name}
                      </a>
                    ) : (
                      s.name
                    )}
                    {s.district ? `, ${title(s.district)}` : ""}
                    {s.tier ? ` · ${s.tier}` : ""}
                    {s.stage ? ` · ${s.stage}` : ""}
                    <br />
                    <small>
                      {s.about} (shares: {s.shared_words.join(", ")})
                    </small>
                  </li>
                ))}
              </ol>
            </>
          ) : null}
          {out.sector_companies && out.sector_companies.total ? (
            <>
              <h3>Registered companies in {title(sector)}</h3>
              <p>
                {out.sector_companies.total.toLocaleString("en-IN")} in all
                {out.sector_companies.median_year ? `, typically registered around ${out.sector_companies.median_year}` : ""};{" "}
                {out.sector_companies.registered_since_2015.toLocaleString("en-IN")} since 2015.
              </p>
              <Table caption="By district" counts={out.sector_companies.by_district} />
              <p>
                <small>{out.sector_companies.source}</small>
              </p>
            </>
          ) : null}
          <p>
            <small>{out.coverage}</small>
          </p>
        </>
      ) : null}
    </section>
  );
}

function ForAProgramme() {
  const [ids, setIds] = useState("");
  const [out, setOut] = useState<Programme | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session_ids = ids.split(/[\s,]+/).map((x) => x.trim()).filter(Boolean);
      setOut(await post<Programme>("/api/v1/cohort/programme", { session_ids }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h2>For an incubator: your founders together</h2>
      <p>
        Counts across your founders' ideation sessions. Only founders who agreed to share are counted;
        nothing is shown under 5 of them; groups under 5 are merged; no idea or name is ever shown.
      </p>
      <form onSubmit={run}>
        <p>
          <label htmlFor="cohort-ids">Session IDs, one per line</label>
          <br />
          <textarea id="cohort-ids" rows={4} cols={70} value={ids} onChange={(e) => setIds(e.target.value)} />
        </p>
        <p>
          <button type="submit" disabled={busy || !ids.trim()}>
            {busy ? "Counting…" : "Summarise"}
          </button>
        </p>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {out ? (
        <>
          <p>
            {out.sessions_found} session(s) found; {out.founders_sharing} founder(s) agreed to share.
          </p>
          {out.shown ? (
            <>
              {Object.entries(out.where_they_are ?? {}).map(([k, c]) => (
                <Table key={k} caption={title(k)} counts={c} />
              ))}
              {Object.entries(out.their_ideas ?? {}).map(([k, c]) => (
                <Table key={k} caption={title(k)} counts={c} />
              ))}
              <Table caption="Not worked out yet" counts={out.not_worked_out_yet ?? {}} />
              {out.progress ? (
                <p>
                  On average {Math.round(out.progress.average_share_of_essentials_known * 100)}% of the
                  essentials are known; {out.progress.reached_a_roadmap} reached a roadmap.
                </p>
              ) : null}
              <p>
                <small>{out.privacy}</small>
              </p>
            </>
          ) : (
            <p>{out.reason}</p>
          )}
        </>
      ) : null}
    </section>
  );
}

export default function Cohort() {
  return (
    <section>
      <h1>Cohort</h1>
      <ForAnIdea />
      <hr />
      <ForAProgramme />
    </section>
  );
}
