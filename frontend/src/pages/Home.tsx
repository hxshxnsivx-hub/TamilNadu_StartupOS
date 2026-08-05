import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Band,
  Cell,
  Cornice,
  Empty,
  FreeRule,
  Hara,
  Magnetic,
  Masthead,
  Page,
  Rail,
  RailPanel,
  Register,
  Setting,
  Stat,
  Uncover,
} from "../design/atelier";
import { useScrollProgress, useWallTone } from "../components/Wall";
import NewsBoard from "../components/NewsBoard";
import Journey from "../scene/Journey";
import { api } from "../api";

/* Honest numbers only. There is no logo wall on this page because there are
   no customers yet, and fabricating them would be worse than omitting them. */
const PROOF = [
  { label: "Schemes checked", value: 8 },
  { label: "Readiness axes", value: 6 },
  { label: "Languages", value: 3 },
];

export default function Home() {
  const { t } = useTranslation();
  const [online, setOnline] = useState<boolean | null>(null);
  const proofRef = useRef<HTMLDivElement>(null);

  useWallTone();
  useScrollProgress(proofRef);

  useEffect(() => {
    let alive = true;
    api
      .version()
      .then(() => alive && setOnline(true))
      .catch(() => alive && setOnline(false));
    return () => {
      alive = false;
    };
  }, []);

  /* The four mazes a founder is actually lost in, in the order they hit. */
  const chapters = [
    {
      n: "01",
      to: "/ideate",
      title: t("c1_t"),
      ta: "யோசனை",
      body: t("c1_d"),
      tone: "var(--mayil)",
    },
    {
      n: "02",
      to: "/schemes",
      title: t("c2_t"),
      ta: "திட்டங்கள்",
      body: t("c2_d"),
      tone: "var(--arakku)",
    },
    {
      n: "03",
      to: "/b2b",
      title: t("c3_t"),
      ta: "ஒத்துழைப்பு",
      body: t("c3_d"),
      tone: "var(--manthulir)",
    },
    {
      n: "04",
      to: "/funding",
      title: t("c4_t"),
      ta: "நிதி",
      body: t("c4_d"),
      tone: "var(--brass-deep)",
    },
  ];

  return (
    <Page set="home">
      <Masthead
        bleed
        index="Tamil Nadu StartupOS"
        status={online === null ? "…" : online ? t("connected") : t("offline")}
        lines={["From idea", <>to <em>enterprise</em>.</>]}
        ta="வணிகம் — உங்கள் மொழியில், தொடக்கம் முதல் நிறுவனம் வரை."
        lede={t("subtitle")}
        actions={
          <>
            <Magnetic>
              <Link to="/ideate" className="btn primary">
                {t("get_started")}
              </Link>
            </Magnetic>
            <Link to="/schemes" className="btn ghost">
              {t("schemes")}
            </Link>
          </>
        }
      />

      <Journey />

      {/* ---- the arc, pinned and advancing sideways ---- */}
      <Rail count={chapters.length} tone="chapters">
        {chapters.map((c, i) => (
          <RailPanel
            key={c.n}
            n={c.n}
            to={c.to}
            title={c.title}
            ta={c.ta}
            step={`Step ${i + 1} of ${chapters.length}`}
            body={c.body}
            cta={t("open")}
            tone={c.tone}
          />
        ))}
      </Rail>

      {/* ---- the proof: the claim this product is actually making ---- */}
      <Band depth={1} tone="statement" className="v-proof" invert folio="II">
        <div className="v-proof-in" ref={proofRef}>
          <Hara />

          <div className="v-stats">
            {PROOF.map((s, i) => (
              <Stat key={s.label} label={s.label} value={s.value} index={i} />
            ))}
          </div>

          <div className="v-split v-proof-split">
            <Setting
              as="h2"
              className="v-pull"
              lines={["Every answer carries", "its reason. Every", "refusal its remedy."]}
              stagger={100}
            />

            <Uncover delay={300}>
              <p className="v-aside v-lead" lang="en">
                Eligibility is decided by explicit rules, not opinion. A “no” always
                names the rule it failed and what would change it — so the platform
                can be argued with, and audited.
              </p>
              <FreeRule delay={420} />
              <p className="v-note">Deterministic · Explainable · Offline-testable</p>
            </Uncover>
          </div>
        </div>
      </Band>

      {/* ---- what changed this week, for a founder in Tamil Nadu ---- */}
      <Band
        depth={2}
        tone="work"
        folio="III"
        title={["What changed this week"]}
        index="Schemes · Funding · Policy"
      >
        <NewsBoard limit={6} />
      </Band>

      {/* ---- the three things this page has to answer before you leave ---- */}
      <Band depth={3} tone="work" folio="IV">
        <span className="v-vlabel">The contract</span>
        <Register>
          <Cell span={5} tall label="01 — The claim">
            <p className="v-aside">
              Similarity-based recommenders surface schemes a founder is legally
              ineligible for. That wastes months and destroys trust. Every result
              here is proven against hard constraints before it is shown.
            </p>
            <Link to="/schemes" className="btn ghost">
              {t("schemes")}
            </Link>
          </Cell>

          <Cell span={4} label="02 — The language">
            <p className="v-aside">
              English, தமிழ் and हिंदी are first-class, not a translation layer
              bolted on afterwards.
            </p>
          </Cell>

          <Cell span={3} label="03 — The cost">
            <p className="v-aside">No sign-up to try. Nothing stored until you say so.</p>
          </Cell>

          {/* the near-empty quadrant — what makes the field read as composed
              rather than filled. It is deliberately given nothing. */}
          <Cell span={3} quiet />

          <Cell span={5} label="04 — When nothing matches">
            <Empty
              title="Rejection is the roadmap"
              body="A search that returns nothing still knows exactly what blocked you. That list is the most useful thing on the page, so it is shown ranked rather than hidden behind an apology."
              fixes={[
                { label: "Register your entity", count: 28 },
                { label: "Reach 80% profile completeness", count: 11 },
                { label: "Obtain DPIIT recognition", count: 6 },
              ]}
            />
          </Cell>

          <Cell span={4} label="05 — Start here">
            <p className="v-aside">
              Whether or not you have an idea yet, the first step is the same.
            </p>
            <Link to="/ideate" className="btn primary">
              {t("get_started")}
            </Link>
          </Cell>
        </Register>
      </Band>

      {/* ---- the funnel's final action: the page must not just stop ---- */}
      <Band depth={3} className="v-close">
        <Cornice />
        <div className="v-split">
          <div>
            <Setting
              as="h2"
              className="v-pull"
              lines={["Start where", "you actually are."]}
            />
            <p className="v-mast-ta" lang="ta">
              யோசனை இருந்தாலும், இல்லாவிட்டாலும் — இங்கிருந்து தொடங்குங்கள்.
            </p>
          </div>

          <div className="v-stack">
            <div className="v-row">
              <Magnetic>
                <Link to="/ideate" className="btn primary">
                  {t("get_started")}
                </Link>
              </Magnetic>
              <Link to="/register" className="btn ghost">
                {t("register")}
              </Link>
            </div>
            <dl className="v-colophon">
              <div>
                <dt>Access</dt>
                <dd className="v-colophon-v">No sign-up to try. Nothing stored until you say so.</dd>
              </div>
              <div>
                <dt>Languages</dt>
                <dd className="v-colophon-v">English · தமிழ் · हिंदी, by text and voice</dd>
              </div>
              <div>
                <dt>Method</dt>
                <dd className="v-colophon-v">
                  Constraint-solved, not similarity-ranked. Every result carries
                  its reason and every refusal its remedy.
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </Band>
    </Page>
  );
}
