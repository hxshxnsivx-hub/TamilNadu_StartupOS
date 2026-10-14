/* Journey: which registrations a startup needs, why, and in what order.
 *
 * The founder answers a few plain questions; every step comes back with its
 * status (required, recommended, not needed, or not decided yet), the reason,
 * the documents, the official link, and what it waits on. Ticking a step done
 * moves the "do next" list on. Nothing is decided on a guess: a step that
 * depends on an unanswered question says "not decided yet" and names the question.
 *
 * Answers and ticks stay in this browser only (no account needed).
 */

import { useEffect, useMemo, useState } from "react";

type Facts = Record<string, string | number | boolean | null>;

interface Step {
  id: string;
  phase: string;
  title: string;
  why: string;
  documents: string[];
  link: string | null;
  days: string | null;
  fee: string | null;
  confidence: string;
  status: "required" | "recommended" | "not_needed" | "unknown" | "done";
  reason: string;
  advice: string[];
  waiting_on: string[];
}

interface Question {
  fact: string;
  ask: string;
  kind?: "bool" | "int";
  choices?: string[];
}

interface JourneyOut {
  steps: Step[];
  next: string[];
  questions: Question[];
  counts: Record<string, number>;
  checked_on: string;
  note: string;
}

const KEY = "vanigam_journey";
const STATUS: Record<Step["status"], string> = {
  required: "Required",
  recommended: "Recommended",
  not_needed: "Not needed",
  unknown: "Not decided yet",
  done: "Done",
};
const ENTITY: Record<string, string> = {
  none: "No legal structure yet",
  proprietorship: "Proprietorship",
  partnership: "Partnership",
  llp: "LLP",
  pvt_ltd: "Private limited company",
  opc: "One-person company",
};
const DISTRICTS = ["chennai", "coimbatore", "madurai", "tiruchirappalli", "salem", "tirunelveli", "erode", "tiruppur", "vellore", "thanjavur"];

function load(): { facts: Facts; done: string[] } {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* private window: start empty */
  }
  return { facts: {}, done: [] };
}

function persist(facts: Facts, done: string[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ facts, done }));
  } catch {
    /* the page still works; it just will not remember */
  }
}

async function fetchJourney(facts: Facts, done: string[]): Promise<JourneyOut> {
  const clean = Object.fromEntries(Object.entries(facts).filter(([, v]) => v !== null && v !== ""));
  const res = await fetch("/api/v1/journey", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ facts: clean, done }),
  });
  if (!res.ok) throw new Error(`The journey could not be worked out (${res.status}).`);
  return res.json();
}

/* One question, answered in place. */
function Ask({ q, value, onChange }: { q: Question; value: Facts[string]; onChange: (v: Facts[string]) => void }) {
  const id = `fact-${q.fact}`;
  if (q.choices) {
    return (
      <p>
        <label htmlFor={id}>{q.ask}</label>{" "}
        <select id={id} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">Choose…</option>
          {q.choices.map((c) => (
            <option key={c} value={c}>
              {ENTITY[c] ?? c}
            </option>
          ))}
        </select>
      </p>
    );
  }
  if (q.kind === "int") {
    return (
      <p>
        <label htmlFor={id}>{q.ask}</label>{" "}
        <input
          id={id}
          type="number"
          min={0}
          value={value === null || value === undefined ? "" : String(value)}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        />
      </p>
    );
  }
  return (
    <fieldset>
      <legend>{q.ask}</legend>
      {(
        [
          ["Yes", true],
          ["No", false],
        ] as const
      ).map(([label, v]) => (
        <label key={label}>
          <input
            type="radio"
            name={id}
            value={label}
            aria-label={label}
            checked={value === v}
            onChange={() => onChange(v)}
          />{" "}
          {label}{" "}
        </label>
      ))}
    </fieldset>
  );
}

export default function Journey() {
  const saved = useMemo(load, []);
  const [facts, setFacts] = useState<Facts>(saved.facts);
  const [done, setDone] = useState<string[]>(saved.done);
  const [data, setData] = useState<JourneyOut | null>(null);
  const [asked, setAsked] = useState<Question[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    persist(facts, done);
    let live = true;
    fetchJourney(facts, done)
      .then((d) => {
        if (!live) return;
        setData(d);
        setError("");
        // keep every question that has been shown, so an answered one stays editable
        setAsked((prev) => {
          const seen = new Map(prev.map((q) => [q.fact, q]));
          for (const q of d.questions) if (!seen.has(q.fact)) seen.set(q.fact, q);
          return [...seen.values()];
        });
      })
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [facts, done]);

  const set = (fact: string, v: Facts[string]) => setFacts((f) => ({ ...f, [fact]: v }));
  const toggle = (id: string) => setDone((d) => (d.includes(id) ? d.filter((x) => x !== id) : [...d, id]));
  const byPhase = useMemo(() => {
    const out = new Map<string, Step[]>();
    for (const s of data?.steps ?? []) out.set(s.phase, [...(out.get(s.phase) ?? []), s]);
    return [...out.entries()];
  }, [data]);
  const title = (id: string) => data?.steps.find((s) => s.id === id)?.title ?? id;
  const open = (data?.questions ?? []).filter((q) => facts[q.fact] === undefined || facts[q.fact] === null);

  return (
    <section>
      <h1>Your registration journey</h1>
      <p>
        Which registrations your startup needs, why, and in what order. Answer what you know; a step that
        depends on something you have not answered says so, instead of guessing.
      </p>

      <h2>About your business</h2>
      <p>
        <label htmlFor="fact-district">District</label>{" "}
        <select
          id="fact-district"
          value={(facts.district as string) ?? ""}
          onChange={(e) => set("district", e.target.value || null)}
        >
          <option value="">Choose…</option>
          {DISTRICTS.map((d) => (
            <option key={d} value={d}>
              {d[0].toUpperCase() + d.slice(1)}
            </option>
          ))}
        </select>
      </p>
      {asked.map((q) => (
        <Ask key={q.fact} q={q} value={facts[q.fact] ?? null} onChange={(v) => set(q.fact, v)} />
      ))}
      {open.length ? <p>{open.length} question(s) above would settle the steps marked "not decided yet".</p> : null}
      <p>
        <button
          type="button"
          onClick={() => {
            setFacts({});
            setDone([]);
            setAsked([]);
          }}
        >
          Start again
        </button>
      </p>

      {error ? <p role="alert">{error}</p> : null}

      {data ? (
        <>
          <h2>Do next</h2>
          {data.next.length ? (
            <ol>
              {data.next.map((id) => (
                <li key={id}>{title(id)}</li>
              ))}
            </ol>
          ) : (
            <p>Nothing is ready to start yet: answer the questions above, or tick off the steps you have done.</p>
          )}
          <p>
            {Object.entries(data.counts)
              .map(([k, n]) => `${STATUS[k as Step["status"]] ?? k}: ${n}`)
              .join(" · ")}
          </p>

          {byPhase.map(([phase, steps]) => (
            <div key={phase}>
              <h2>{phase}</h2>
              {steps.map((s) => (
                <article key={s.id}>
                  <h3>
                    <label>
                      <input
                        type="checkbox"
                        checked={s.status === "done"}
                        disabled={s.status === "not_needed"}
                        onChange={() => toggle(s.id)}
                      />{" "}
                      {s.title}
                    </label>{" "}
                    <small>({STATUS[s.status]})</small>
                  </h3>
                  <p>{s.why}</p>
                  {s.reason ? (
                    <p>
                      <em>For you:</em> {s.reason}
                    </p>
                  ) : null}
                  {s.waiting_on.length ? <p>Waits on: {s.waiting_on.map(title).join(", ")}</p> : null}
                  {s.documents.length ? <p>Documents: {s.documents.join(", ")}</p> : null}
                  <p>
                    {s.days ? `About ${s.days} day(s). ` : ""}
                    {s.fee ? `Fee: ${s.fee}. ` : ""}
                    {s.link ? (
                      <a href={s.link} target="_blank" rel="noreferrer">
                        Official site
                      </a>
                    ) : null}
                    {s.confidence === "to_verify" ? " · confirm with the authority" : ""}
                  </p>
                  {s.advice.length ? (
                    <ul>
                      {s.advice.map((a) => (
                        <li key={a}>{a}</li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              ))}
            </div>
          ))}
          <p>
            <small>
              {data.note} Checked on {data.checked_on}.
            </small>
          </p>
        </>
      ) : null}
    </section>
  );
}
