import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type BOMLine, type DecomposeOut } from "../api";
import {
  Band,
  Dial,
  Empty,
  Masthead,
  Page,
  Pending,
  Plate,
  PlateHead,
  Shelf,
  Stepper,
  Uncover,
  Waiting,
  bandOf,
} from "../design/atelier";

/* Product decomposition → bill of materials → supplier map.
 *
 * The one rule that shapes this whole screen: **the generated BOM is a
 * draft.** The spec requires a human to confirm or edit it before matching is
 * acted on, so the flow is deliberately three steps and the middle one cannot
 * be skipped. An auto-committed BOM would have the founder sourcing parts a
 * language model guessed at.
 *
 * Named TN industrial clusters are surfaced for gap lines because a gap is
 * only useful if it comes with somewhere to look. */

const STEPS = ["Describe", "Confirm the BOM", "Supply map"];

const TONE: Record<string, string> = {
  high: "var(--oxide-green)",
  mid: "var(--oxide-mustard)",
  low: "var(--oxide-red)",
};

/* Sourced clusters, offered only against a gap line. Kept short and honest —
   these are places to look, not vendors we have verified. */
const CLUSTERS: Record<string, string> = {
  pump: "Coimbatore — pumps and motors",
  yarn: "Tiruppur — knitwear and yarn",
  dye: "Tiruppur — dyeing and processing",
  leather: "Ambur–Ranipet — leather",
  printing: "Sivakasi — printing and packaging",
  packaging: "Sivakasi — printing and packaging",
  pcb: "Hosur — electronics",
  sensor: "Hosur — electronics",
};

function clusterFor(category: string): string | null {
  const key = Object.keys(CLUSTERS).find((k) => category.toLowerCase().includes(k));
  return key ? CLUSTERS[key] : null;
}

export default function Supply() {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    product: "solar powered cold storage unit",
    monthly_units: 500,
    district: "Madurai",
    state: "Tamil Nadu",
  });
  const [data, setData] = useState<DecomposeOut | null>(null);
  const [bom, setBom] = useState<BOMLine[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: string, v: unknown) => setForm((x) => ({ ...x, [k]: v }));
  const step = !data ? 0 : !confirmed ? 1 : 2;

  async function decompose() {
    setErr(null);
    setBusy(true);
    setData(null);
    setConfirmed(false);
    try {
      const r = await api.decompose({
        product: form.product,
        monthly_units: Number(form.monthly_units),
        district: form.district,
        state: form.state,
      });
      setData(r);
      // the draft is copied into editable state — the response itself is
      // never treated as the confirmed BOM
      setBom(r.bom.map((l) => ({ ...l })));
    } catch (e: any) {
      setErr(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  function editLine(i: number, k: keyof BOMLine, v: string) {
    setBom((x) =>
      x.map((l, idx) =>
        idx === i ? { ...l, [k]: k === "qty_per_unit" ? Number(v) : v } : l,
      ),
    );
  }

  function dropLine(i: number) {
    setBom((x) => x.filter((_, idx) => idx !== i));
  }

  /* The map is built FROM the confirmed BOM, not filtered from the response.
     That ordering matters. Filtering the response would mean a line the
     founder renamed — which is exactly what they are invited to do — silently
     vanished from the map instead of showing up as unmatched. A line with no
     join is a gap, which is a real and useful answer; a line that disappears
     is a bug that looks like data. */
  const byCategory = new Map(
    (data?.supply_map ?? []).map((m) => [m.line.category.toLowerCase(), m]),
  );
  const shownMap = bom.map((line) => {
    const hit = byCategory.get(line.category.toLowerCase());
    return hit && hit.matches.length > 0
      ? { line, gap: false, matches: hit.matches }
      : { line, gap: true, matches: [] };
  });
  const gapCount = shownMap.filter((m) => m.gap).length;

  return (
    <Page set="b2b">
      <Masthead
        index="Supply feasibility"
        lines={[t("supply_title")]}
        lede={t("supply_lede")}
        aside={
          <div className="v-intake">
            <label className="v-fld">
              <span>What you want to make</span>
              <input
                value={form.product}
                onChange={(e) => set("product", e.target.value)}
              />
            </label>
            <div className="v-grid2">
              <label className="v-fld">
                <span>Units / month</span>
                <input
                  type="number"
                  value={form.monthly_units}
                  onChange={(e) => set("monthly_units", e.target.value)}
                />
              </label>
              <label className="v-fld">
                <span>District</span>
                <input
                  value={form.district}
                  onChange={(e) => set("district", e.target.value)}
                />
              </label>
            </div>
            <Shelf note={`${form.monthly_units}/mo · ${form.district}`}>
              <button
                className="btn primary"
                onClick={decompose}
                disabled={busy || form.product.trim().length < 2}
              >
                {busy ? t("loading") : "Decompose"}
              </button>
            </Shelf>
            {err && <div className="v-err">{err}</div>}
          </div>
        }
      />

      <Band depth={3} tone="work">
        <Stepper steps={STEPS} at={step} />
      </Band>

      {busy && (
        <Band depth={3}>
          <Waiting label={t("loading")} />
          <Pending rows={2} />
        </Band>
      )}

      {data && !busy && (
        <>
          {/* ---------- step 2 · the draft, which must be confirmed ---------- */}
          <Band
            depth={2}
            tone="statement"
            folio="I"
            title={["The draft bill of materials"]}
            index={`${bom.length} lines · per unit`}
          >
            <Uncover>
              <p className="v-aside">
                This was generated, not verified. Edit anything that is wrong and
                remove anything you do not need — nothing is matched against
                suppliers until you confirm it below.
              </p>
            </Uncover>

            {bom.length === 0 ? (
              <Empty
                title="Every line removed"
                body="Add the product back or decompose again — there is nothing left to source."
              />
            ) : (
              <div className="v-bom" role="table" aria-label="Bill of materials">
                <div className="v-bom-head" role="row">
                  <span role="columnheader">Category</span>
                  <span role="columnheader">Specification</span>
                  <span role="columnheader">Qty / unit</span>
                  <span role="columnheader">Unit</span>
                  <span role="columnheader">
                    <span className="v-sr">Remove</span>
                  </span>
                </div>

                {bom.map((l, i) => (
                  <div className="v-bom-row" role="row" key={`${l.category}-${i}`}>
                    <label className="v-fld">
                      <span className="v-sr">Category</span>
                      <input
                        value={l.category}
                        onChange={(e) => editLine(i, "category", e.target.value)}
                      />
                    </label>
                    <label className="v-fld">
                      <span className="v-sr">Specification</span>
                      <input
                        value={l.spec}
                        onChange={(e) => editLine(i, "spec", e.target.value)}
                      />
                    </label>
                    <label className="v-fld">
                      <span className="v-sr">Quantity per unit</span>
                      <input
                        type="number"
                        step="any"
                        value={l.qty_per_unit}
                        onChange={(e) => editLine(i, "qty_per_unit", e.target.value)}
                      />
                    </label>
                    <label className="v-fld">
                      <span className="v-sr">Unit</span>
                      <input
                        value={l.unit}
                        onChange={(e) => editLine(i, "unit", e.target.value)}
                      />
                    </label>
                    <button
                      className="v-bom-drop"
                      onClick={() => dropLine(i)}
                      aria-label={`Remove ${l.category}`}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <Shelf
              note={
                confirmed
                  ? "Confirmed — the map below reflects your edits"
                  : "Nothing is matched until you confirm"
              }
            >
              <button
                className="btn primary"
                onClick={() => setConfirmed(true)}
                disabled={confirmed || bom.length === 0}
              >
                {confirmed ? "Confirmed" : "Confirm this BOM"}
              </button>
              {confirmed && (
                <button className="btn ghost" onClick={() => setConfirmed(false)}>
                  Edit again
                </button>
              )}
            </Shelf>
          </Band>

          {/* ---------- step 3 · the map ---------- */}
          {confirmed && (
            <Band
              depth={3}
              tone="work"
              folio="II"
              title={["Supply map"]}
              index={`${shownMap.length} lines · ${gapCount} with no supplier`}
            >
              <div className="v-tree">
                {shownMap.map((m, i) => {
                  const cluster = clusterFor(m.line.category);
                  return (
                    <section
                      className={m.gap ? "v-branch is-gap" : "v-branch"}
                      key={`${m.line.category}-${i}`}
                    >
                      <header className="v-branch-head">
                        <span className="v-branch-cat">{m.line.category}</span>
                        <span className="v-branch-spec">{m.line.spec}</span>
                        <span className="v-branch-qty">
                          {m.line.qty_per_unit} {m.line.unit}/unit ·{" "}
                          {Math.round(m.line.qty_per_unit * data.monthly_units)}{" "}
                          {m.line.unit}/mo
                        </span>
                        <span className={m.gap ? "v-tag v-tag-gap" : "v-tag"}>
                          {m.gap ? "no supplier" : `${m.matches.length} matched`}
                        </span>
                      </header>

                      {m.gap ? (
                        <div className="v-branch-gap">
                          <p className="v-aside">
                            Nothing on the platform covers this line yet.
                            {cluster
                              ? ` The nearest place to look is ${cluster}.`
                              : ""}
                          </p>
                          <button className="btn ghost" type="button">
                            Invite a vendor for this line
                          </button>
                        </div>
                      ) : (
                        <div className="v-grid">
                          {m.matches.slice(0, 3).map((mt, k) => (
                            <Plate
                              key={mt.supply.id}
                              index={k}
                              tone={TONE[bandOf(mt.weight)]}
                            >
                              <PlateHead
                                eyebrow={
                                  <>
                                    <span className="v-tag">{mt.supply.district}</span>
                                    <span className="v-tag is-quiet">
                                      trust {mt.supply.trust_score}
                                    </span>
                                  </>
                                }
                                title={mt.supply.name}
                                figure={<Dial value={mt.weight} caption="match" size={56} />}
                              />
                              <dl className="v-facts">
                                <div>
                                  <dt>price</dt>
                                  <dd>
                                    ₹{mt.supply.unit_price}
                                    <i>/unit</i>
                                  </dd>
                                </div>
                                <div>
                                  <dt>capacity</dt>
                                  <dd>
                                    {mt.supply.max_capacity.toLocaleString()}
                                    <i>/mo</i>
                                  </dd>
                                </div>
                              </dl>
                            </Plate>
                          ))}
                        </div>
                      )}
                    </section>
                  );
                })}
              </div>

              {gapCount > 0 && (
                <Uncover>
                  <p className="v-note">
                    {gapCount} of {shownMap.length} lines have no supplier on the
                    platform. That is a real answer, not a failure — it tells you
                    where the supply chain has to be built.
                  </p>
                </Uncover>
              )}
            </Band>
          )}
        </>
      )}
    </Page>
  );
}
