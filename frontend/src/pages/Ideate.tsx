import { useMemo, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { api, type RoadmapOut } from "../api";
import {
  loadJourney,
  saveJourney,
  type MilestoneStatus,
} from "../journeyStore";
import {
  Band,
  Cell,
  Dial,
  Masthead,
  Meter,
  Page,
  Pending,
  Rail,
  Register,
  Shelf,
  Stat,
  Uncover,
  Waiting,
} from "../design/atelier";

/* Milestone tracking is held in the browser alongside the rest of the
   founder's journey. Status is a three-state enum, not a checkbox: a
   milestone that has been STARTED and one that has not are different
   situations, and collapsing them loses the only signal that tells you
   whether a roadmap is actually moving. */
const NEXT: Record<MilestoneStatus, MilestoneStatus> = {
  pending: "in_progress",
  in_progress: "done",
  done: "pending",
};

const STATUS_LABEL: Record<MilestoneStatus, string> = {
  pending: "Not started",
  in_progress: "In progress",
  done: "Done",
};

/* Each phase carries its own oxide. Six phases, one pigment each, drawn from
   the Athangudi set so the timeline never leaves the palette. */
const PHASE: Record<string, string> = {
  Ideation: "var(--oxide-mustard)",
  Validation: "var(--oxide-indigo)",
  MVP: "var(--oxide-green)",
  Launch: "var(--brass-deep)",
  Growth: "var(--oxide-red)",
  Scale: "var(--arakku)",
};

export default function Ideate() {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [data, setData] = useState<RoadmapOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function generate() {
    setErr(null);
    setBusy(true);
    setData(null);
    try {
      setData(await api.roadmap(text));
    } catch (e: any) {
      setErr(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  const dims = data ? Object.entries(data.feasibility_breakdown) : [];

  // tracking state, keyed by milestone id
  const [track, setTrack] = useState(() => loadJourney().milestones);

  function cycle(id: string) {
    setTrack((prev) => {
      const cur = prev[id]?.status ?? "pending";
      const next = NEXT[cur];
      const now = new Date().toISOString();
      const rec = {
        status: next,
        notes: prev[id]?.notes ?? "",
        started_at:
          next === "in_progress" ? now : (prev[id]?.started_at ?? null),
        completed_at: next === "done" ? now : null,
      };
      const merged = { ...prev, [id]: rec };
      saveJourney({ ...loadJourney(), milestones: merged });
      return merged;
    });
  }

  const progress = useMemo(() => {
    if (!data) return { done: 0, active: 0, pct: 0 };
    const done = data.milestones.filter((m) => track[m.id]?.status === "done").length;
    const active = data.milestones.filter(
      (m) => track[m.id]?.status === "in_progress",
    ).length;
    return {
      done,
      active,
      pct: data.milestones.length
        ? Math.round((done / data.milestones.length) * 100)
        : 0,
    };
  }, [data, track]);

  return (
    <Page set="ideate">
      <Masthead
        index={t("ideate_nav")}
        lines={[t("ideate_title")]}
        ta="யோசனை இருந்தாலும், இல்லாவிட்டாலும் — இங்கிருந்து தொடங்குங்கள்."
        lede={t("ideate_hint")}
        aside={
          <div className="v-intake">
            <label className="v-fld">
              <span>{t("ideate_hint")}</span>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={t("ideate_placeholder")}
                rows={6}
              />
            </label>
            <Shelf note={`${text.trim().length} characters`}>
              <button
                className="btn primary"
                onClick={generate}
                disabled={busy || text.trim().length < 3}
              >
                {busy ? t("loading") : t("generate")}
              </button>
            </Shelf>
            {err && <div className="v-err">{err}</div>}
          </div>
        }
      />

      {busy && (
        <Band depth={3}>
          <Waiting label={t("loading")} />
          <Pending rows={2} />
        </Band>
      )}

      {data && !busy && (
        <>
          {/* ---- the assessment, as one compartmented field ---- */}
          <Band depth={2} tone="statement" invert folio="I">
            <Register>
              <Cell span={4} tall label="Feasibility">
                <Dial value={data.feasibility_score} caption="score" size={132} />
                {data.idea.domain ? (
                  <span className="v-tag">{data.idea.domain}</span>
                ) : null}
              </Cell>

              <Cell span={5} tall label={t("feasibility")}>
                <div className="v-stack">
                  {dims.map(([k, v], i) => (
                    <Meter key={k} label={k} value={v} index={i} />
                  ))}
                </div>
              </Cell>

              <Cell span={3} label="Critical path">
                <p className="v-aside">
                  {data.critical_path.length} of {data.milestones.length} milestones
                  are on the path that decides the date. Everything else can slip.
                </p>
              </Cell>

              {/* the near-empty compartment — the field reads as composed
                  because one region of it is left alone */}
              <Cell span={3} quiet />

              {data.clarifications.length > 0 ? (
                <Cell span={12} label={t("improve")}>
                  <ol className="v-steps">
                    {data.clarifications.map((c, i) => (
                      <li key={i} style={{ "--d": `${i * 62}ms` } as CSSProperties}>
                        <span className="v-steps-n">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span>{c}</span>
                      </li>
                    ))}
                  </ol>
                </Cell>
              ) : null}
            </Register>
          </Band>

          {/* ---- the roadmap, pinned and advancing sideways ----
              5–15 milestones would be 15 screens of vertical scroll. Pinning
              the band and moving it laterally spends the same scroll on one
              screen of height, and the sequence stays readable as a sequence
              rather than a list. */}
          <Band
            depth={3}
            tone="chapters"
            folio="II"
            title={[t("roadmap_title")]}
            index={`${data.milestones.length} milestones · ${data.critical_path.length} critical`}
          >
            <Uncover>
              <p className="v-aside">
                {t("critical_path")}:{" "}
                {data.critical_path.map((s, i) => (
                  <b className="v-path" key={`${s}-${i}`}>
                    {s}
                  </b>
                ))}
              </p>
            </Uncover>
          </Band>

          {/* ---- what is actually moving ---- */}
          <Band depth={3} tone="statement">
            <div className="v-stats">
              <Stat label="Milestones done" value={progress.done} index={0} />
              <Stat label="In progress" value={progress.active} index={1} />
              <Stat label="Complete" value={progress.pct} suffix="%" index={2} />
            </div>
            <p className="v-note">
              Tracked in this browser · {data.milestones.length} milestones ·
              realistic estimate{" "}
              {data.milestones.reduce((a, m) => a + m.timeline.realistic, 0)} months
              end to end
            </p>
          </Band>

          {/* count is the real number of milestones; screens caps how much
              scroll it costs, so a 15-milestone roadmap does not turn the
              page into a corridor. Travel is measured, not derived from
              either number. */}
          <Rail
            count={data.milestones.length}
            screens={Math.min(data.milestones.length, 5)}
            tone="chapters"
          >
            {data.milestones.map((m) => {
              const st: MilestoneStatus = track[m.id]?.status ?? "pending";
              return (
              <article
                key={m.id}
                className={[
                  "v-rail-panel",
                  m.critical && "is-crit",
                  st === "done" && "is-done",
                  st === "in_progress" && "is-active",
                ]
                  .filter(Boolean)
                  .join(" ")}
                style={
                  { "--tone": PHASE[m.phase] || "var(--hair-2)" } as CSSProperties
                }
              >
                <span className="v-rail-n">{m.phase}</span>
                <h3 className="v-rail-t">{m.title}</h3>

                <div className="v-row">
                  {m.critical ? (
                    <span className="v-tag">{t("critical_path")}</span>
                  ) : null}
                  <span className="v-tag is-quiet">
                    ~{m.timeline.realistic} mo
                  </span>
                </div>

                <div className="v-chips">
                  {m.deliverables.map((dl, k) => (
                    <span className="v-chip" key={k}>
                      {dl}
                    </span>
                  ))}
                </div>

                {m.depends_on.length > 0 ? (
                  <p className="v-note">
                    {t("depends")} {m.depends_on.join(", ")}
                  </p>
                ) : null}

                {/* one control, three states, cycling in the order work
                    actually happens. aria-pressed would be wrong here —
                    this is not a toggle. */}
                <button
                  className={`v-track v-track-${st}`}
                  onClick={() => cycle(m.id)}
                >
                  <span className="v-track-dot" aria-hidden="true" />
                  {STATUS_LABEL[st]}
                  <span className="v-track-next" aria-hidden="true">
                    → {STATUS_LABEL[NEXT[st]]}
                  </span>
                </button>

                <i className="v-rail-edge" aria-hidden="true" />
              </article>
              );
            })}
          </Rail>
        </>
      )}
    </Page>
  );
}
