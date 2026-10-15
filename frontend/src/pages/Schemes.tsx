import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type RecommendOut } from "../api";
import {
  Band,
  Chips,
  Dial,
  Empty,
  Masthead,
  Meter,
  Page,
  Pending,
  Plate,
  PlateHead,
  Provenance,
  Reasons,
  Shelf,
  Uncover,
  Waiting,
  bandOf,
} from "../design/atelier";

const GENDER = ["", "male", "female", "non_binary"];
const CASTE = ["", "general", "obc", "sc", "st", "ews"];
const STAGE = ["idea", "poc", "prototype", "mvp", "revenue", "growth", "scale"];
const ENTITY = ["private_limited", "llp", "opc", "partnership", "sole_proprietor"];

/* Which pigment carries each tier of government. Two chromatics on any one
   card, never three — the level tag and the korvai edge. */
const LEVEL_TONE: Record<string, string> = {
  central: "var(--oxide-indigo)",
  state: "var(--oxide-green)",
  bank: "var(--oxide-mustard)",
};

const clamp = (v: number) => Math.max(0, Math.min(100, Math.round(Number(v) || 0)));

const TONE: Record<string, string> = {
  high: "var(--oxide-green)",
  mid: "var(--oxide-mustard)",
  low: "var(--oxide-red)",
};

export default function Schemes() {
  const { t } = useTranslation();
  const [f, setF] = useState({
    state: "Tamil Nadu",
    gender: "female",
    caste_category: "sc",
    age: 30,
    first_graduate: true,
    stage: "idea",
    entity_type: "private_limited",
    dpiit_recognized: true,
    incorporation_age_years: 1,
    annual_revenue: 500000,
    funding_need: 1200000,
  });
  const [data, setData] = useState<RecommendOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: string, v: unknown) => setF((x) => ({ ...x, [k]: v }));

  async function find() {
    setErr(null);
    setBusy(true);
    setData(null);
    try {
      setData(
        await api.recommendSchemes({
          founder: {
            state: f.state,
            gender: f.gender || undefined,
            caste_category: f.caste_category || undefined,
            age: Number(f.age),
            first_graduate: f.first_graduate,
          },
          startup: {
            stage: f.stage,
            entity_type: f.entity_type,
            dpiit_recognized: f.dpiit_recognized,
            incorporation_age_years: Number(f.incorporation_age_years),
            annual_revenue: Number(f.annual_revenue),
          },
          funding_need: Number(f.funding_need) || null,
        }),
      );
    } catch (e: any) {
      setErr(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page set="schemes">
      <Masthead
        index={t("schemes")}
        lines={[t("schemes_title")]}
        lede={t("schemes_hint")}
      />

      <Band depth={3} tone="work">
        <div className="v-form">
          <div className="v-grid2">
            <fieldset className="v-fieldset">
              <legend>Founder</legend>
              <div className="v-grid2">
                <label className="v-fld">
                  <span>State</span>
                  <input value={f.state} onChange={(e) => set("state", e.target.value)} />
                </label>
                <label className="v-fld">
                  <span>Gender</span>
                  <select value={f.gender} onChange={(e) => set("gender", e.target.value)}>
                    {GENDER.map((g) => (
                      <option key={g} value={g}>
                        {g || "—"}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="v-fld">
                  <span>Caste category</span>
                  <select
                    value={f.caste_category}
                    onChange={(e) => set("caste_category", e.target.value)}
                  >
                    {CASTE.map((c) => (
                      <option key={c} value={c}>
                        {c || "—"}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="v-fld">
                  <span>Age</span>
                  <input
                    type="number"
                    value={f.age}
                    onChange={(e) => set("age", e.target.value)}
                  />
                </label>
              </div>
              <div className="v-checks">
                <label className="v-fld is-check">
                  <input
                    type="checkbox"
                    checked={f.first_graduate}
                    onChange={(e) => set("first_graduate", e.target.checked)}
                  />
                  <span>First graduate</span>
                </label>
              </div>
            </fieldset>

            <fieldset className="v-fieldset">
              <legend>Startup</legend>
              <div className="v-grid2">
                <label className="v-fld">
                  <span>Startup stage</span>
                  <select value={f.stage} onChange={(e) => set("stage", e.target.value)}>
                    {STAGE.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="v-fld">
                  <span>Entity type</span>
                  <select
                    value={f.entity_type}
                    onChange={(e) => set("entity_type", e.target.value)}
                  >
                    {ENTITY.map((s) => (
                      <option key={s} value={s}>
                        {s.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="v-fld">
                  <span>Funding need (₹)</span>
                  <input
                    type="number"
                    value={f.funding_need}
                    onChange={(e) => set("funding_need", e.target.value)}
                  />
                </label>
              </div>
              <div className="v-checks">
                <label className="v-fld is-check">
                  <input
                    type="checkbox"
                    checked={f.dpiit_recognized}
                    onChange={(e) => set("dpiit_recognized", e.target.checked)}
                  />
                  <span>DPIIT recognized</span>
                </label>
              </div>
            </fieldset>
          </div>

          <Shelf
            note={`${f.stage} · ${f.entity_type.replace(/_/g, " ")} · ${f.state}`}
          >
            <button className="btn primary" onClick={find} disabled={busy}>
              {busy ? t("loading") : t("find_schemes")}
            </button>
          </Shelf>

          {err && <div className="v-err">{err}</div>}
        </div>
      </Band>

      {busy && (
        <Band depth={3}>
          <Waiting label={t("loading")} />
          <Pending />
        </Band>
      )}

      {data && !busy && (
        <>
          <Band
            depth={2}
            tone="statement"
            folio="I"
            title={[t("eligible_label")]}
            index={`${data.ranked_eligible.length} of ${data.total_checked} checked`}
          >
            {data.ranked_eligible.length === 0 ? (
              <Empty
                title="Nothing cleared every rule yet"
                body="No scheme passed the full constraint set for this profile. The refusals below name the exact rule each one stopped at — change one field above and search again."
              />
            ) : (
              <div className="v-grid">
                {data.ranked_eligible.map((r, i) => (
                  <Plate
                    key={r.scheme.id}
                    index={i}
                    tone={TONE[bandOf(clamp(r.relevance))]}
                  >
                    <PlateHead
                      eyebrow={
                        <>
                          <span
                            className="v-tag"
                            style={{
                              background: "transparent",
                              border: "1px solid currentColor",
                              color: LEVEL_TONE[r.scheme.level] || "var(--ink-4)",
                            }}
                          >
                            {r.scheme.level}
                          </span>
                          <span className="v-tag is-quiet">{r.scheme.type}</span>
                        </>
                      }
                      title={r.scheme.name}
                      meta={r.scheme.benefits}
                      figure={<Dial value={r.relevance} caption="relevance" />}
                    />

                    <Meter label="likelihood" value={r.likelihood} />
                    <Chips items={r.why} />

                    <Provenance href={r.scheme.source_url}>
                      {t("verified_on")} {r.scheme.last_verified}
                    </Provenance>
                  </Plate>
                ))}
              </div>
            )}
          </Band>

          {data.ineligible.length > 0 && (
            <Band
              depth={3}
              tone="work"
              folio="II"
              title={[t("ineligible_label")]}
              index={`${data.ineligible.length} · shown, not hidden`}
            >
              <Uncover>
                <p className="v-aside">
                  A refusal is more useful than a silence. Each card below names the
                  constraint it failed, so you can see exactly what would have to
                  change.
                </p>
              </Uncover>

              <div className="v-grid">
                {data.ineligible.map((it, i) => (
                  <Plate key={it.scheme.id} index={i} off>
                    <PlateHead
                      eyebrow={
                        <>
                          <span className="v-tag is-quiet">{it.scheme.level}</span>
                          <span className="v-tag is-quiet">{it.scheme.type}</span>
                        </>
                      }
                      title={it.scheme.name}
                    />

                    <Reasons label={t("reasons_label")} items={it.reasons} refusal />

                    <Provenance href={it.scheme.source_url}>
                      {t("verified_on")} {it.scheme.last_verified}
                    </Provenance>
                  </Plate>
                ))}
              </div>
            </Band>
          )}
        </>
      )}
    </Page>
  );
}
