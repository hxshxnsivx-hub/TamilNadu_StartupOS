import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type NewsBoardOut } from "../api";
import {
  Band,
  Empty,
  Masthead,
  Page,
  Pending,
  Stat,
  Uncover,
  Waiting,
} from "../design/atelier";
import NewsBoard from "../components/NewsBoard";

/* The vernacular news board, given its own surface.
 *
 * It was already built and the endpoint was already live; it just had no
 * route, so it only ever appeared as a six-item strip on the landing page.
 *
 * Two things this screen must be honest about, both required by the spec:
 *  · summaries are machine-generated and labelled as such
 *  · the agent-status strip shows which sources were actually reachable, so a
 *    thin board reads as "four sources were down" rather than "nothing
 *    happened this week"
 */

export default function Intel() {
  const { t } = useTranslation();
  const [meta, setMeta] = useState<NewsBoardOut | null>(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .newsBoard({ limit: 24 })
      .then((r) => alive && setMeta(r))
      .catch((e) => alive && setErr(e.message || "Failed"))
      .finally(() => alive && setBusy(false));
    return () => {
      alive = false;
    };
  }, []);

  const reachable = meta?.sources.filter((s) => s.fetchable).length ?? 0;
  const verified = meta?.sources.filter((s) => s.verified).length ?? 0;

  return (
    <Page set="schemes">
      <Masthead
        index="Intelligence"
        status={meta ? (meta.is_live ? "live" : "cached") : "…"}
        lines={[t("intel_title")]}
        lede={t("intel_lede")}
      />

      {meta && (
        <Band depth={3} tone="statement" invert folio="I">
          <div className="v-stats">
            <Stat label="Items" value={meta.items.length} index={0} />
            <Stat label="Sources reachable" value={reachable} index={1} />
            <Stat label="Sources verified" value={verified} index={2} />
            <Stat label="Fetched" value={meta.total_fetched} index={3} />
          </div>
          {meta.notice && <p className="v-note">{meta.notice}</p>}
        </Band>
      )}

      {busy && (
        <Band depth={3}>
          <Waiting label={t("loading")} />
          <Pending rows={3} />
        </Band>
      )}

      {err && !busy && (
        <Band depth={3}>
          <Empty
            title="The board could not be reached"
            body={err}
            fixes={[{ label: "Check the backend is running on :8000" }]}
          />
        </Band>
      )}

      {!busy && !err && (
        <Band
          depth={3}
          tone="work"
          folio="II"
          title={["The board"]}
          index="Schemes · Funding · Policy"
        >
          <NewsBoard limit={24} />
        </Band>
      )}

      {meta && meta.sources.length > 0 && (
        <Band
          depth={3}
          title={["Where this came from"]}
          index={`${meta.sources.length} sources · ${meta.provider}`}
        >
          <Uncover>
            <p className="v-aside">
              Summaries on the board are generated, not written by a person, and
              every card links the original. A source that could not be fetched
              is listed here rather than silently dropped — a thin board should
              read as "the sources were down", not as "nothing happened".
            </p>
          </Uncover>

          <ul className="v-sources">
            {meta.sources.map((s) => (
              <li
                key={s.id}
                className={s.fetchable ? "v-source" : "v-source is-down"}
              >
                <span className="v-source-dot" aria-hidden="true" />
                <span className="v-source-n">{s.name}</span>
                <span className="v-source-d">{s.domain}</span>
                <span className="v-tag is-quiet">{s.language}</span>
                <span className="v-tag is-quiet">tier {s.tier}</span>
                <span className="v-source-state">
                  {s.fetchable ? "reachable" : "unreachable"}
                  {s.verified ? " · verified" : ""}
                </span>
              </li>
            ))}
          </ul>
        </Band>
      )}
    </Page>
  );
}
