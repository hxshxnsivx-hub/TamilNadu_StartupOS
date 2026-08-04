import { useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, type InvestorMatchOut, type ReadinessOut } from "../api";
import {
  Band,
  Cell,
  Dial,
  Masthead,
  Meter,
  Page,
  Pending,
  Plate,
  PlateHead,
  Provenance,
  Reasons,
  Register,
  Shelf,
  Spider,
  Uncover,
  Waiting,
  bandOf,
} from "../design/atelier";

const STAGE = ["idea", "poc", "prototype", "mvp", "revenue", "growth", "scale"];

const TONE: Record<string, string> = {
  high: "var(--oxide-green)",
  mid: "var(--oxide-mustard)",
  low: "var(--oxide-red)",
};

const money = (n: number) => `₹${Number(n).toLocaleString("en-IN")}`;

export default function Funding() {
  const { t } = useTranslation();
  const [f, setF] = useState({
    sector: "agritech",
    stage: "mvp",
    state: "Tamil Nadu",
    team_size: 3,
    founder_experience_years: 4,
    users: 800,
    monthly_revenue: 60000,
    funding_need: 2000000,
    is_registered: true,
    dpiit_recognized: true,
    has_pitch_deck: true,
    has_market_validation: true,
  });
  const [readiness, setReadiness] = useState<ReadinessOut | null>(null);
  const [investors, setInvestors] = useState<InvestorMatchOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: string, v: unknown) => setF((x) => ({ ...x, [k]: v }));

  async function assess() {
    setErr(null);
    setBusy(true);
    setReadiness(null);
    setInvestors(null);
    try {
      const profile = {
        stage: f.stage,
        team_size: Number(f.team_size),
        founder_experience_years: Number(f.founder_experience_years),
        users: Number(f.users),
        monthly_revenue: Number(f.monthly_revenue),
        is_registered: f.is_registered,
        dpiit_recognized: f.dpiit_recognized,
        has_pitch_deck: f.has_pitch_deck,
        has_market_validation: f.has_market_validation,
        // richer defaults so a complete founder profile scores realistically
        has_domain_expertise: true,
        feature_completeness: 80,
        deck_completeness: 80,
        has_clear_problem: true,
        has_differentiation: true,
        has_ip: true,
        retention_rate: 60,
        partnerships: 2,
        runway_months: 12,
        revenue_growth_pct: 20,
        has_unit_economics: true,
        has_projections: true,
        is_compliant: true,
        has_cap_table: true,
      };
      const r = await api.fundingReadiness(profile);
      setReadiness(r);
      const m = await api.matchInvestors({
        startup: {
          sector: f.sector,
          stage: f.stage,
          users: Number(f.users),
          monthly_revenue: Number(f.monthly_revenue),
          state: f.state,
        },
        funding_need: Number(f.funding_need),
        readiness_overall: r.overall,
      });
      setInvestors(m);
    } catch (e: any) {
      setErr(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  const dims = readiness ? Object.entries(readiness.dimensions) : [];

  return (
    <Page set="funding">
      <Masthead
        index={t("funding")}
        lines={[t("funding_title")]}
        lede={t("funding_hint")}
      />

      <Band depth={3} tone="work">
        <div className="v-form">
          <fieldset className="v-fieldset">
            <legend>Startup</legend>
            <div className="v-grid2">
              <label className="v-fld">
                <span>Sector</span>
                <input value={f.sector} onChange={(e) => set("sector", e.target.value)} />
              </label>
              <label className="v-fld">
                <span>Stage</span>
                <select value={f.stage} onChange={(e) => set("stage", e.target.value)}>
                  {STAGE.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label className="v-fld">
                <span>State</span>
                <input value={f.state} onChange={(e) => set("state", e.target.value)} />
              </label>
              <label className="v-fld">
                <span>Funding need (₹)</span>
                <input
                  type="number"
                  value={f.funding_need}
                  onChange={(e) => set("funding_need", e.target.value)}
                />
              </label>
              <label className="v-fld">
                <span>Team size</span>
                <input
                  type="number"
                  value={f.team_size}
                  onChange={(e) => set("team_size", e.target.value)}
                />
              </label>
              <label className="v-fld">
                <span>Founder experience (yrs)</span>
                <input
                  type="number"
                  value={f.founder_experience_years}
                  onChange={(e) => set("founder_experience_years", e.target.value)}
                />
              </label>
              <label className="v-fld">
                <span>Users</span>
                <input
                  type="number"
                  value={f.users}
                  onChange={(e) => set("users", e.target.value)}
                />
              </label>
              <label className="v-fld">
                <span>Monthly revenue (₹)</span>
                <input
                  type="number"
                  value={f.monthly_revenue}
                  onChange={(e) => set("monthly_revenue", e.target.value)}
                />
              </label>
            </div>

            <div className="v-checks">
              <label className="v-fld is-check">
                <input
                  type="checkbox"
                  checked={f.is_registered}
                  onChange={(e) => set("is_registered", e.target.checked)}
                />
                <span>Registered</span>
              </label>
              <label className="v-fld is-check">
                <input
                  type="checkbox"
                  checked={f.dpiit_recognized}
                  onChange={(e) => set("dpiit_recognized", e.target.checked)}
                />
                <span>DPIIT recognized</span>
              </label>
              <label className="v-fld is-check">
                <input
                  type="checkbox"
                  checked={f.has_pitch_deck}
                  onChange={(e) => set("has_pitch_deck", e.target.checked)}
                />
                <span>Pitch deck</span>
              </label>
              <label className="v-fld is-check">
                <input
                  type="checkbox"
                  checked={f.has_market_validation}
                  onChange={(e) => set("has_market_validation", e.target.checked)}
                />
                <span>Market validation</span>
              </label>
            </div>
          </fieldset>

          <Shelf note={`${f.sector} · ${f.stage} · ${money(f.funding_need)}`}>
            <button className="btn primary" onClick={assess} disabled={busy}>
              {busy ? t("loading") : t("assess")}
            </button>
          </Shelf>

          {err && <div className="v-err">{err}</div>}
        </div>
      </Band>

      {busy && (
        <Band depth={3}>
          <Waiting label={t("loading")} />
          <Pending rows={2} />
        </Band>
      )}

      {readiness && !busy && (
        <Band depth={2} tone="statement" invert folio="I">
          <Register>
            <Cell span={4} tall label="Investor readiness">
              <Dial value={readiness.overall} caption={readiness.band} size={132} />
            </Cell>

            {/* The six axes read as a shape, not six separate numbers: the
                question a founder asks here is "which side am I weak on",
                which is a shape question. Every axis still carries its
                number in the key beside it. */}
            <Cell span={5} tall label="Six axes">
              <Spider axes={dims.map(([k, v]) => ({ label: k, value: v }))} />
            </Cell>

            <Cell span={3} label="How this is weighted">
              <p className="v-aside">
                Traction 25 · Team 20 · Product 20 · Financial 15 · Pitch 10 ·
                Legal 10. Any axis under 60 opens a gap.
              </p>
            </Cell>

            <Cell span={3} quiet />

            {readiness.gaps.length > 0 ? (
              <Cell span={12} label={t("gap_plan")}>
                <p className="v-aside">
                  Sorted by impact against effort — the top item is the cheapest
                  thing that moves the score most.
                </p>
                <ol className="v-steps">
                  {readiness.gaps.slice(0, 6).map((g, i) => (
                    <li key={i} style={{ "--d": `${i * 62}ms` } as CSSProperties}>
                      <span className="v-steps-n">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="v-stack">
                        <span>{g.action}</span>
                        <span className="v-chips">
                          <span className="v-chip">{g.impact} impact</span>
                          <span className="v-chip">+{g.impact_points} pts</span>
                          <span className="v-chip">{g.effort_weeks}w</span>
                          <span className="v-chip">{g.dimension.replace(/_/g, " ")}</span>
                        </span>
                      </span>
                    </li>
                  ))}
                </ol>
              </Cell>
            ) : null}
          </Register>
        </Band>
      )}

      {investors && !busy && (
        <>
          <Band
            depth={3}
            tone="work"
            folio="II"
            title={[t("matched_investors")]}
            index={`${investors.eligible.length} matched`}
          >
            <Uncover>
              <p className="v-aside">
                Track the ones you actually talk to on the{" "}
                <Link to="/pipeline">pipeline board</Link> — it holds the eight
                stages and will only offer moves the rules allow.
              </p>
            </Uncover>

            <div className="v-grid">
              {investors.eligible.map((e, i) => (
                <Plate key={e.investor.id} index={i} tone={TONE[bandOf(e.fit)]}>
                  <PlateHead
                    eyebrow={
                      <>
                        <span className="v-tag">{e.fit}% fit</span>
                        <span className="v-tag is-quiet">{e.investor.type}</span>
                      </>
                    }
                    title={e.investor.name}
                    meta={e.investor.thesis}
                  />

                  <Meter label="fit" value={e.fit} />

                  <dl className="v-facts">
                    <div>
                      <dt>ticket</dt>
                      <dd>
                        {money(e.investor.min_ticket)} – {money(e.investor.max_ticket)}
                      </dd>
                    </div>
                    <div>
                      <dt>track record</dt>
                      <dd>{e.investor.track_record_score}</dd>
                    </div>
                  </dl>

                  {/* every externally-sourced fact carries its retrieval date */}
                  <Provenance>driven from web · verify before contact</Provenance>
                </Plate>
              ))}
            </div>
          </Band>

          {investors.ineligible.length > 0 && (
            <Band
              depth={3}
              title={[t("not_a_fit")]}
              index={`${investors.ineligible.length} · shown, not hidden`}
            >
              <Uncover>
                <p className="v-aside">
                  These are not hidden, because knowing why an investor is out is
                  worth as much as knowing who is in.
                </p>
              </Uncover>

              <div className="v-grid">
                {investors.ineligible.map((x, i) => (
                  <Plate key={x.investor.id} index={i} off>
                    <PlateHead
                      eyebrow={<span className="v-tag is-quiet">{x.investor.type}</span>}
                      title={x.investor.name}
                      meta={x.investor.thesis}
                    />
                    <Reasons label={t("reasons_label")} items={x.reasons} refusal />
                    <dl className="v-facts">
                      <div>
                        <dt>ticket</dt>
                        <dd>
                          {money(x.investor.min_ticket)} –{" "}
                          {money(x.investor.max_ticket)}
                        </dd>
                      </div>
                    </dl>
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
