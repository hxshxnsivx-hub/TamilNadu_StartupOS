import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth";
import { scoreProfile } from "../completeness";
import { loadProfile } from "../profileStore";
import {
  Band,
  Cell,
  Dial,
  Masthead,
  Page,
  Register,
  Shelf,
  Uncover,
  useCount,
} from "../design/atelier";

/* Category → the tier at which it unlocks. Mirrors the spec's gating. */
const CATS = [
  { n: "01", t: "c1_t", d: "c1_d", unlock: 40, to: "/ideate", tone: "var(--mayil)" },
  { n: "02", t: "c2_t", d: "c2_d", unlock: 80, to: "/schemes", tone: "var(--arakku)" },
  { n: "03", t: "c3_t", d: "c3_d", unlock: 60, to: "/b2b", tone: "var(--manthulir)" },
  { n: "04", t: "c4_t", d: "c4_d", unlock: 100, to: "/funding", tone: "var(--brass-deep)" },
];

/* Completeness is categorical, not continuous — 40 / 60 / 80 / 100 are the
   only values it can take. So this is four discrete gates, drawn as gates,
   not a smooth bar pretending to a precision the score does not have. */
const GATES = [40, 60, 80, 100];

export default function Dashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const s = scoreProfile(loadProfile());

  const pct = useCount(s.score, 1000);
  const next = GATES.find((g) => g > s.score) ?? null;

  return (
    <Page set="account">
      <Masthead
        index={t("welcome")}
        status={user?.email}
        lines={[t("welcome")]}
        lede={t("dash_hint")}
        actions={
          <Link to="/profile" className="btn primary">
            {s.score < 100 ? t("complete_profile") : t("edit_profile")}
          </Link>
        }
      />

      <Band depth={3} tone="statement">
        <Register>
          <Cell span={4} tall label={t("completeness")}>
            <Dial value={s.score} caption={t("tier_" + s.tier)} size={132} />
          </Cell>

          <Cell span={8} tall label="Gates">
            <div className="v-gates">
              {GATES.map((g) => {
                const passed = s.score >= g;
                return (
                  <div
                    key={g}
                    className={passed ? "v-gate is-passed" : "v-gate"}
                    aria-label={`${g}% ${passed ? "passed" : "not reached"}`}
                  >
                    <span className="v-gate-n">{g}%</span>
                    <span className="v-gate-bar" />
                  </div>
                );
              })}
            </div>

            <p className="v-aside">
              {next !== null
                ? `You are at ${pct}%. The next gate is ${next}% — the profile page lists exactly which fields open it.`
                : `You are at ${pct}%. Every gate is open.`}
            </p>

            <Shelf note={next !== null ? `Next gate ${next}%` : "All gates open"}>
              <Link to="/profile" className="btn ghost">
                {t("complete_profile")}
              </Link>
            </Shelf>
          </Cell>
        </Register>
      </Band>

      <Band
        depth={3}
        tone="work"
        title={[t("categories")]}
        index={`${CATS.filter((c) => s.score >= c.unlock).length} of ${CATS.length} open`}
      >
        <Register>
          {CATS.map((c) => {
            const open = s.score >= c.unlock;
            const progress = Math.min(100, Math.round((s.score / c.unlock) * 100));
            return (
              <Cell key={c.n} span={6} label={c.n}>
                <div
                  className={open ? "v-catcard is-open" : "v-catcard"}
                  style={{ ["--tone" as string]: c.tone }}
                >
                  <h3 className="v-plate-t">{t(c.t)}</h3>
                  <p className="v-aside">{t(c.d)}</p>

                  {open ? (
                    <Link to={c.to} className="v-rail-go">
                      {t("open")} <span aria-hidden="true">→</span>
                    </Link>
                  ) : (
                    <>
                      {/* a lock that shows the distance is a task; a lock that
                          shows only a padlock is a wall */}
                      <span className="v-lockbar" aria-hidden="true">
                        <span style={{ width: `${progress}%` }} />
                      </span>
                      <span className="v-note">
                        {s.score}% of {c.unlock}% needed
                      </span>
                    </>
                  )}
                </div>
              </Cell>
            );
          })}
        </Register>
      </Band>

      <Band depth={3}>
        <Uncover>
          <p className="v-aside">
            Nothing here is stored on a server until you save it. The completeness
            score is computed in the browser from the profile draft you hold.
          </p>
        </Uncover>
      </Band>
    </Page>
  );
}
