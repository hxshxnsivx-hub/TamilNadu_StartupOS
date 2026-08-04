import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ApiError,
  api,
  type PipelineBoardOut,
  type PipelineEntry,
} from "../api";
import {
  Band,
  Empty,
  Masthead,
  Page,
  Pending,
  Reasons,
  Stat,
  Uncover,
  Waiting,
} from "../design/atelier";

/* The funding pipeline.
 *
 * The board is computed server-side (/funding/pipeline/board) and every stage
 * move is validated server-side (/pipeline/advance). That matters: the stage
 * machine is a rule, not a UI convention, and re-implementing it here would
 * let the two drift.
 *
 * The board offers plausible moves and lets the server refuse. It does not
 * pre-check them, because the server's refusal already carries the remedy —
 * "Cannot skip stages — next is 'pitch_delivered'", with the allowed set in
 * `suggestions[]`. Showing that is strictly more useful than hiding a button,
 * and it is the same contract every other refusal in this product uses.
 *
 * Entries live in this browser. There is no persistence endpoint yet, so the
 * board is honest about being local rather than pretending to be synced. */

const KEY = "vanigam_pipeline";

const STAGE_LABEL: Record<string, string> = {
  initial_contact: "Initial contact",
  pitch_scheduled: "Pitch scheduled",
  pitch_delivered: "Pitch delivered",
  due_diligence: "Due diligence",
  term_sheet: "Term sheet",
  negotiation: "Negotiation",
  closed_won: "Closed — won",
  closed_lost: "Closed — lost",
};

const money = (n: number) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

function load(): PipelineEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as PipelineEntry[]) : [];
  } catch {
    return [];
  }
}

function save(e: PipelineEntry[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(e));
  } catch {
    /* storage unavailable — the session still works, it just won't persist */
  }
}

export default function Pipeline() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<PipelineEntry[]>(() => load());
  const [board, setBoard] = useState<PipelineBoardOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  /* Per-card refusals. The stage machine lives on the server, so rather than
     probing it (which costs a request and produces an error by design), the
     board offers the plausible moves and lets the server refuse — then shows
     the refusal WITH the remedy it came with. That is the same contract every
     other screen in this product uses: a "no" always names the rule it failed
     and what would change it. */
  const [refusal, setRefusal] = useState<
    Record<string, { message: string; suggestions: string[] }>
  >({});

  const refresh = useCallback(async (list: PipelineEntry[]) => {
    setErr(null);
    setBusy(true);
    try {
      setBoard(await api.pipelineBoard(list));
    } catch (e: any) {
      setErr(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    refresh(entries);
    // deliberately once on mount; every mutation calls refresh itself, so a
    // dependency on `entries` here would double-fetch on every advance
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persist(list: PipelineEntry[]) {
    setEntries(list);
    save(list);
    refresh(list);
  }

  function add() {
    const n = entries.length + 1;
    persist([
      ...entries,
      {
        investor_id: `local-${Date.now()}`,
        investor_name: `Investor ${n}`,
        stage: "initial_contact",
        amount: 2000000,
        history: [{ stage: "initial_contact", at: new Date().toISOString() }],
      },
    ]);
  }

  async function advance(entry: PipelineEntry, to: string) {
    try {
      const r = await api.pipelineAdvance(entry, to);
      persist(entries.map((e) => (e.investor_id === entry.investor_id ? r.entry : e)));
      setRefusal((x) => {
        const { [entry.investor_id]: _drop, ...rest } = x;
        return rest;
      });
    } catch (e: unknown) {
      const ae = e as ApiError;
      setRefusal((x) => ({
        ...x,
        [entry.investor_id]: {
          message: ae?.message ?? "Could not move this conversation",
          suggestions: ae?.suggestions ?? [],
        },
      }));
    }
  }

  function remove(id: string) {
    persist(entries.filter((e) => e.investor_id !== id));
  }

  function rename(id: string, name: string) {
    const list = entries.map((e) =>
      e.investor_id === id ? { ...e, investor_name: name } : e,
    );
    setEntries(list);
    save(list);
  }

  function setAmount(id: string, amount: number) {
    const list = entries.map((e) => (e.investor_id === id ? { ...e, amount } : e));
    setEntries(list);
    save(list);
    refresh(list);
  }

  const m = board?.metrics;

  /* Candidates come from the stage order the SERVER sent with the board, not
     from a list hardcoded here — so adding a stage backend-side surfaces
     without a frontend change. The two terminal stages are always offerable;
     the server has the final say on both. */
  function candidates(stage: string): string[] {
    const stages = board?.stages ?? [];
    const i = stages.indexOf(stage);
    if (i < 0) return [];
    const out: string[] = [];
    const linear = stages.filter((s) => !s.startsWith("closed_"));
    const li = linear.indexOf(stage);
    if (li >= 0 && li + 1 < linear.length) out.push(linear[li + 1]);
    for (const s of stages) if (s.startsWith("closed_") && s !== stage) out.push(s);
    return out;
  }

  return (
    <Page set="funding">
      <Masthead
        index="Pipeline"
        lines={[t("pipeline_title")]}
        lede={t("pipeline_lede")}
        aside={
          <div className="v-intake">
            <div className="v-row">
              <button className="btn primary" onClick={add}>
                Add a conversation
              </button>
              <Link to="/funding" className="btn ghost">
                Find investors
              </Link>
            </div>
            {err && <div className="v-err">{err}</div>}
          </div>
        }
      />

      {m && (
        <Band depth={3} tone="statement" invert folio="I">
          <div className="v-stats">
            <Stat label="Open" value={m.open_count} index={0} />
            <Stat label="Won" value={m.won} index={1} />
            <Stat label="Win rate" value={m.win_rate} suffix="%" index={2} />
            <Stat label="Weighted ₹L" value={Math.round(m.weighted_value / 100000)} index={3} />
          </div>
          <p className="v-note">
            Pipeline {money(m.pipeline_value)} · weighted {money(m.weighted_value)} ·{" "}
            {m.total} total · {m.lost} lost
          </p>
        </Band>
      )}

      {busy && !board && (
        <Band depth={3}>
          <Waiting label="Computing the board" />
          <Pending rows={2} />
        </Band>
      )}

      {board && entries.length === 0 && (
        <Band depth={3}>
          <Empty
            title="No conversations yet"
            body="Add one for each investor you are actually talking to. The board will then tell you where your pipeline is thin — which is usually the useful part."
            fixes={board.stages.slice(0, 4).map((s) => ({ label: STAGE_LABEL[s] ?? s }))}
          />
        </Band>
      )}

      {board && entries.length > 0 && (
        <Band
          depth={3}
          tone="work"
          folio="II"
          title={["The board"]}
          index={`${board.columns.length} stages · scrolls sideways`}
        >
          <div className="v-kanban" role="list">
            {board.columns.map((col) => (
              <section className="v-col" role="listitem" key={col.stage}>
                <header className="v-col-head">
                  <span className="v-col-t">{STAGE_LABEL[col.stage] ?? col.stage}</span>
                  <span className="v-col-n">{col.count}</span>
                  <span className="v-col-v">{money(col.value)}</span>
                </header>

                <div className="v-col-body">
                  {col.entries.length === 0 ? (
                    <p className="v-col-empty">—</p>
                  ) : (
                    col.entries.map((e) => {
                      const next = candidates(e.stage);
                      const no = refusal[e.investor_id];
                      return (
                        <article className="v-card" key={e.investor_id}>
                          <label className="v-fld">
                            <span className="v-sr">Investor name</span>
                            <input
                              value={e.investor_name ?? ""}
                              onChange={(ev) => rename(e.investor_id, ev.target.value)}
                            />
                          </label>

                          <label className="v-fld">
                            <span className="v-sr">Amount</span>
                            <input
                              type="number"
                              value={e.amount}
                              onChange={(ev) =>
                                setAmount(e.investor_id, Number(ev.target.value) || 0)
                              }
                            />
                          </label>

                          <span className="v-note">{money(e.amount)}</span>

                          <div className="v-chips">
                            {next.length === 0 ? (
                              <span className="v-chip">terminal stage</span>
                            ) : (
                              next.map((s) => (
                                <button
                                  key={s}
                                  className="v-chip v-chip-go"
                                  onClick={() => advance(e, s)}
                                >
                                  → {STAGE_LABEL[s] ?? s}
                                </button>
                              ))
                            )}
                          </div>

                          {no && (
                            <Reasons
                              label={no.message}
                              items={no.suggestions}
                              refusal
                            />
                          )}

                          <button
                            className="v-card-drop"
                            onClick={() => remove(e.investor_id)}
                            aria-label={`Remove ${e.investor_name}`}
                          >
                            ×
                          </button>
                        </article>
                      );
                    })
                  )}
                </div>
              </section>
            ))}
          </div>

          <Uncover>
            <p className="v-note">
              Which stages you may move to is decided by the server, not by this
              screen — so the board can never offer a transition the rules
              forbid.
            </p>
          </Uncover>
        </Band>
      )}
    </Page>
  );
}
