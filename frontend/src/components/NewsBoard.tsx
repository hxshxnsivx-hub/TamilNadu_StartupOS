/* The news board (Task 6.1 · P-44).
 *
 * Every item states where it came from, when, and why it was ranked where it
 * is. The board also states plainly whether the corpus is live — a board that
 * looked authoritative while serving a demonstration set would mislead a
 * founder acting on a deadline, which is the one thing it must not do.
 */

import { useEffect, useState } from "react";
import { api, type NewsBoardOut } from "../api";

const TIER_LABEL: Record<string, string> = {
  government: "Official",
  mainstream: "Press",
  trade: "Trade",
  aggregator: "Aggregator",
};

function daysAgo(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  const days = Math.round((Date.now() - d.getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  return iso;
}

export default function NewsBoard({
  founder,
  limit = 6,
}: {
  founder?: Record<string, unknown>;
  limit?: number;
}) {
  const [data, setData] = useState<NewsBoardOut | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .newsBoard({ founder, limit })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setErr(e.message || "Could not load"));
    return () => {
      alive = false;
    };
    // founder is a literal in practice; limit is stable
  }, [limit]);

  if (err) {
    return (
      <p className="nb-empty">
        The news board is unavailable right now. Everything else still works.
      </p>
    );
  }

  if (!data) {
    return (
      <div className="nb-grid" aria-busy="true">
        {Array.from({ length: 3 }, (_, i) => (
          <div className="nb-item nb-skel" key={i} />
        ))}
      </div>
    );
  }

  const govCount = data.sources.filter((s) => s.tier === "government").length;

  return (
    <div className="nb">
      {/* provenance strip — the honesty line, not a decoration */}
      <div className={data.is_live ? "nb-strip" : "nb-strip nb-demo"}>
        <span className="nb-dot" aria-hidden="true" />
        <span className="nb-strip-t">
          {data.is_live ? "Live" : "Demonstration corpus"}
        </span>
        <span className="nb-strip-d">{data.notice}</span>
      </div>

      <ol className="nb-grid">
        {data.items.map((item) => (
          <li className="nb-item" key={item.id}>
            <a
              className="nb-link"
              href={item.url}
              target="_blank"
              rel="noopener noreferrer nofollow"
            >
              <div className="nb-meta">
                <span className={`nb-tier nb-tier-${item.tier}`}>
                  {TIER_LABEL[item.tier] || item.tier}
                </span>
                <span className="nb-src">{item.source_name}</span>
                <span className="nb-when">{daysAgo(item.published)}</span>
              </div>

              <h3 className="nb-title" lang={item.language}>
                {item.title}
              </h3>
              <p className="nb-sum" lang={item.language}>
                {item.summary}
              </p>

              {item.why.length > 0 && (
                <ul className="nb-why">
                  {item.why.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              )}

              {item.duplicates.length > 0 && (
                <p className="nb-dupe">
                  Also reported by {item.duplicates.length} other source
                  {item.duplicates.length > 1 ? "s" : ""}
                </p>
              )}
            </a>
          </li>
        ))}
      </ol>

      <p className="nb-foot">
        Ranked across {data.sources.length} allowlisted sources — {govCount} official.
        Summaries are ours; follow any headline for the publisher's full article.
      </p>
    </div>
  );
}
