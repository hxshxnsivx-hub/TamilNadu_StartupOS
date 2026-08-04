import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type B2BMatchOut } from "../api";
import {
  Band,
  Dial,
  Empty,
  Masthead,
  Meter,
  Page,
  Pending,
  Plate,
  PlateHead,
  Shelf,
  Waiting,
  bandOf,
} from "../design/atelier";

const CATEGORIES = ["yarn", "dye", "packaging", "pcb", "pump", "sensor", "printing"];

const clamp = (v: number) => Math.max(0, Math.min(100, Math.round(Number(v) || 0)));

const TONE: Record<string, string> = {
  high: "var(--oxide-green)",
  mid: "var(--oxide-mustard)",
  low: "var(--oxide-red)",
};

/* The four components of a match weight. Deliberately unlabelled with fixed
   percentages: the split is per-sector configurable server-side, so hardcoding
   "40%" here would be a lie the moment a sector is retuned. */
const BREAKDOWN = [
  ["spec", "spec_similarity"],
  ["price", "price_fit"],
  ["capacity", "capacity_fit"],
  ["geo", "geo_proximity"],
] as const;

export default function B2B() {
  const { t } = useTranslation();
  const [d, setD] = useState({
    category: "yarn",
    spec: "combed cotton yarn 40s count",
    quantity: 2000,
    budget_per_unit: 190,
    district: "Tiruppur",
    state: "Tamil Nadu",
  });
  const [data, setData] = useState<B2BMatchOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: string, v: unknown) => setD((x) => ({ ...x, [k]: v }));

  async function find() {
    setErr(null);
    setBusy(true);
    setData(null);
    try {
      setData(
        await api.matchB2B({
          ...d,
          quantity: Number(d.quantity),
          budget_per_unit: Number(d.budget_per_unit),
        }),
      );
    } catch (e: any) {
      setErr(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page set="b2b">
      <Masthead index={t("b2b")} lines={[t("b2b_title")]} lede={t("b2b_hint")} />

      <Band depth={3} tone="work">
        <div className="v-form">
          <div className="v-grid2">
            <fieldset className="v-fieldset">
              <legend>Requirement</legend>
              <div className="v-grid2">
                <label className="v-fld">
                  <span>What I need</span>
                  <select
                    value={d.category}
                    onChange={(e) => set("category", e.target.value)}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="v-fld">
                  <span>Specification</span>
                  <input value={d.spec} onChange={(e) => set("spec", e.target.value)} />
                </label>
                <label className="v-fld">
                  <span>Quantity / month</span>
                  <input
                    type="number"
                    value={d.quantity}
                    onChange={(e) => set("quantity", e.target.value)}
                  />
                </label>
                <label className="v-fld">
                  <span>Budget per unit (₹)</span>
                  <input
                    type="number"
                    value={d.budget_per_unit}
                    onChange={(e) => set("budget_per_unit", e.target.value)}
                  />
                </label>
              </div>
            </fieldset>

            <fieldset className="v-fieldset">
              <legend>Delivery</legend>
              <div className="v-grid2">
                <label className="v-fld">
                  <span>District</span>
                  <input
                    value={d.district}
                    onChange={(e) => set("district", e.target.value)}
                  />
                </label>
                <label className="v-fld">
                  <span>State</span>
                  <input value={d.state} onChange={(e) => set("state", e.target.value)} />
                </label>
              </div>
            </fieldset>
          </div>

          <Shelf
            note={`${d.category} · ${Number(d.quantity).toLocaleString()}/mo · ₹${d.budget_per_unit} · ${d.district}`}
          >
            <button className="btn primary" onClick={find} disabled={busy}>
              {busy ? t("loading") : t("find_suppliers")}
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
        <Band
          depth={2}
          tone="statement"
          folio="I"
          title={[t("matches_label")]}
          index={`${data.count} · ${data.category}`}
        >
          {data.matches.length === 0 ? (
            <Empty
              title={t("no_suppliers")}
              body="Nothing in this cluster fits the brief yet. A wider budget per unit, a smaller monthly quantity, or a neighbouring district usually opens the list."
            />
          ) : (
            <div className="v-grid">
              {data.matches.map((m, i) => (
                <Plate
                  key={m.supply.id}
                  index={i}
                  tone={TONE[bandOf(clamp(m.weight))]}
                >
                  <PlateHead
                    eyebrow={
                      <>
                        <span className="v-tag">{m.supply.category}</span>
                        {/* trust renders as a number and a mark, so the
                            signal survives greyscale */}
                        <span className="v-tag is-quiet">
                          trust {m.supply.trust_score}
                        </span>
                      </>
                    }
                    title={m.supply.name}
                    figure={<Dial value={m.weight} caption="match" />}
                  />

                  <dl className="v-facts">
                    <div>
                      <dt>price</dt>
                      <dd>
                        ₹{m.supply.unit_price}
                        <i>/unit</i>
                      </dd>
                    </div>
                    <div>
                      <dt>district</dt>
                      <dd>{m.supply.district}</dd>
                    </div>
                    <div>
                      <dt>capacity</dt>
                      <dd>
                        {m.supply.max_capacity.toLocaleString()}
                        <i>/mo</i>
                      </dd>
                    </div>
                    <div>
                      <dt>payment</dt>
                      <dd>{m.supply.payment_mode.replace(/_/g, " ")}</dd>
                    </div>
                  </dl>

                  <div className="v-stack">
                    <div className="v-reasons-h">why this weight</div>
                    {BREAKDOWN.map(([label, key], k) => (
                      <Meter
                        key={key}
                        label={label}
                        value={m.breakdown[key]}
                        index={k}
                      />
                    ))}
                  </div>

                  <p className="v-note">
                    min order {m.supply.min_order.toLocaleString()}
                  </p>
                </Plate>
              ))}
            </div>
          )}
        </Band>
      )}
    </Page>
  );
}
