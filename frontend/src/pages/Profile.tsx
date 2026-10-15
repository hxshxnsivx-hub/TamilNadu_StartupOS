import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { scoreProfile, type ProfileDraft } from "../completeness";
import { loadProfile, saveProfile } from "../profileStore";
import {
  Band,
  Dial,
  Masthead,
  Page,
  Reasons,
  Uncover,
} from "../design/atelier";

const GENDER = ["male", "female", "non_binary", "prefer_not_to_say"];
const CASTE = ["general", "obc", "sc", "st", "ews"];
const ENTITY = ["private_limited", "llp", "opc", "partnership", "sole_proprietor"];
const STAGE = ["idea", "poc", "prototype", "mvp", "revenue", "growth", "scale"];

/* The fields each band is scored on — mirrors completeness.ts, so the
   per-band meters move in step with the dial rather than approximating it. */
const BASIC_SCORED = [
  "name",
  "email",
  "phone",
  "date_of_birth",
  "gender",
  "state",
  "district",
  "city",
];
const EDU_SCORED = ["highest_qualification", "institution", "graduation_year"];
const STARTUP_SCORED = ["startup_name", "entity_type", "domain", "stage"];

function filled(obj: object, keys: string[]): number {
  const rec = obj as Record<string, unknown>;
  return keys.filter((k) => {
    const v = rec?.[k];
    return v !== undefined && v !== null && v !== "";
  }).length;
}

/** A band's legend: number, name, the gate it opens, and a live count. */
function BandLegend({
  no,
  title,
  gate,
  done,
  total,
}: {
  no: string;
  title: string;
  gate: string;
  done: number;
  total: number;
}) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <legend>
      <span className="v-bandhead">
        <span className="v-bandno">{no}</span>
        <span className="v-bandtitle">{title}</span>
        <span className="v-bandgate">opens {gate}</span>
        <span className="v-bandcount" data-full={done === total ? "true" : "false"}>
          {done}/{total}
        </span>
        <span className="v-bandbar" aria-hidden="true">
          <span style={{ width: `${pct}%` }} />
        </span>
      </span>
    </legend>
  );
}

export default function Profile() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [p, setP] = useState<ProfileDraft>(() => loadProfile());
  const s = useMemo(() => scoreProfile(p), [p]);

  // recomputed on every keystroke, so each band answers as it is filled
  const done = useMemo(
    () => ({
      basics: filled(p.founder, BASIC_SCORED),
      edu: filled(p.founder, EDU_SCORED),
      startup: filled(p.startup, STARTUP_SCORED),
      docs: p.docsVerified ? 1 : 0,
    }),
    [p],
  );

  const F = (k: string, v: string | boolean) =>
    setP((x) => ({ ...x, founder: { ...x.founder, [k]: v } }));
  const S = (k: string, v: string) =>
    setP((x) => ({ ...x, startup: { ...x.startup, [k]: v } }));

  function text(label: string, k: keyof ProfileDraft["founder"], type = "text") {
    return (
      <label className="v-fld">
        <span>{label}</span>
        <input
          type={type}
          value={(p.founder[k] as string) ?? ""}
          onChange={(e) => F(k as string, e.target.value)}
        />
      </label>
    );
  }

  function sel(
    label: string,
    k: string,
    opts: string[],
    on: (k: string, v: string) => void,
    val?: string,
  ) {
    return (
      <label className="v-fld">
        <span>{label}</span>
        <select value={val ?? ""} onChange={(e) => on(k, e.target.value)}>
          <option value="">—</option>
          {opts.map((o) => (
            <option key={o} value={o}>
              {o.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </label>
    );
  }

  function save() {
    saveProfile(p);
    nav("/app");
  }

  return (
    <Page set="account">
      <Masthead
        index={t("profile")}
        lines={[t("your_profile")]}
        lede={`${t("completeness")} — ${s.score}%`}
      />

      <Band depth={3} tone="work">
        <div className="v-profile">
          {/* the measure stays beside the form on wide screens and above it on
              narrow ones, so the score is never off-screen while you type */}
          <aside className="v-profile-aside">
            <Dial value={s.score} caption={t("tier_" + s.tier)} size={112} />

            {s.missing.length > 0 && (
              <div aria-live="polite">
                <Reasons
                  label={t("next_tier_needs")}
                  items={s.missing.map((m) =>
                    m.replace(/^(founder|startup|documents)\./, "").replace(/_/g, " "),
                  )}
                />
              </div>
            )}

            <button className="btn primary" onClick={save}>
              {t("save")}
            </button>
          </aside>

          <div className="v-form">
            <fieldset className="v-fieldset">
              <BandLegend
                no="1"
                title={t("basics")}
                gate="40%"
                done={done.basics}
                total={BASIC_SCORED.length}
              />
              <div className="v-grid2">
                {text("Name", "name")}
                {text("Email", "email", "email")}
                {text("Phone", "phone")}
                {text("Date of birth", "date_of_birth", "date")}
                {sel("Gender", "gender", GENDER, F, p.founder.gender)}
                {sel("Caste category", "caste_category", CASTE, F, p.founder.caste_category)}
                {text("State", "state")}
                {text("District", "district")}
                {text("City", "city")}
              </div>
              {/* caste and financial capacity share a protection class in the
                  spec: separate consent, encrypted, purpose-limited */}
              <p className="v-hint">
                Caste category is used only to check reserved-category scheme
                eligibility, and is never shown to partners or investors.
              </p>
            </fieldset>

            <fieldset className="v-fieldset">
              <BandLegend
                no="2"
                title={t("education")}
                gate="60%"
                done={done.edu}
                total={EDU_SCORED.length}
              />
              <div className="v-grid2">
                {text("Highest qualification", "highest_qualification")}
                {text("Institution", "institution")}
                {text("Graduation year", "graduation_year")}
                <label className="v-fld is-check">
                  <input
                    type="checkbox"
                    checked={!!p.founder.first_graduate}
                    onChange={(e) => F("first_graduate", e.target.checked)}
                  />
                  <span>First graduate</span>
                </label>
              </div>
            </fieldset>

            <fieldset className="v-fieldset">
              <BandLegend
                no="3"
                title={t("startup_details")}
                gate="80%"
                done={done.startup}
                total={STARTUP_SCORED.length}
              />
              <div className="v-grid2">
                <label className="v-fld">
                  <span>Startup name</span>
                  <input
                    value={p.startup.startup_name ?? ""}
                    onChange={(e) => S("startup_name", e.target.value)}
                  />
                </label>
                {sel("Entity type", "entity_type", ENTITY, S, p.startup.entity_type)}
                <label className="v-fld">
                  <span>Domain</span>
                  <input
                    value={p.startup.domain ?? ""}
                    onChange={(e) => S("domain", e.target.value)}
                  />
                </label>
                {sel("Stage", "stage", STAGE, S, p.startup.stage)}
              </div>
            </fieldset>

            <fieldset className="v-fieldset">
              <BandLegend
                no="4"
                title={t("docs_verified_demo")}
                gate="100%"
                done={done.docs}
                total={1}
              />
              <label className="v-fld is-check">
                <input
                  type="checkbox"
                  checked={p.docsVerified}
                  onChange={(e) => setP((x) => ({ ...x, docsVerified: e.target.checked }))}
                />
                <span>{t("docs_verified_demo")}</span>
              </label>
            </fieldset>
          </div>
        </div>
      </Band>

      <Band depth={3}>
        <Uncover>
          <p className="v-aside">
            Nothing is sent anywhere until you press save. The draft lives in
            this browser.
          </p>
        </Uncover>
      </Band>

      {/* the aside scrolls away on narrow screens — the save stays in reach */}
      <div className="v-savebar">
        <span className="v-savebar-n">{s.score}%</span>
        <span className="v-savebar-l">{t("tier_" + s.tier)}</span>
        <button className="btn primary" onClick={save}>
          {t("save")}
        </button>
      </div>
    </Page>
  );
}
