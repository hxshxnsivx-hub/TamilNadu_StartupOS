/* Suppliers: real companies to ask, then an order split across the quotes received.
 *
 * Step 1 lists Tamil Nadu companies registered for that kind of supply (MCA
 * master data), nearest first. They are leads, not verified vendors: the page
 * says so, and shows no prices, because the register has none.
 *
 * Step 2 takes the quotes the founder actually received (price, monthly
 * capacity, minimum order) and splits each month's need across them with a
 * solver: cheapest and nearest first, at most a few suppliers per item, and the
 * reason whenever part of the need cannot be met. No invented supplier or price
 * is ever added.
 *
 * Quotes and items stay in this browser only.
 */

import { useEffect, useState } from "react";

const CATEGORIES: Record<string, string> = {
  yarn: "Yarn",
  fabric: "Fabric",
  dye: "Dyes and dyeing",
  printing: "Printing",
  packaging: "Packaging",
  pcb: "Circuit boards (PCB)",
  electronics: "Electronic parts",
  sensor: "Sensors",
  pump: "Pumps",
  motor: "Motors",
  machinery: "Machinery",
  metal_parts: "Metal parts",
  plastic_parts: "Plastic parts",
  chemicals: "Chemicals",
  food_ingredients: "Food ingredients",
  garments: "Garments",
  leather: "Leather",
  furniture: "Furniture",
};
const DISTRICTS = ["chennai", "coimbatore", "madurai", "tiruppur", "salem", "erode", "tiruchirappalli", "vellore", "kancheepuram", "tirunelveli", "krishnagiri", "virudhunagar"];
const KEY = "vanigam_suppliers";
const cap = (s: string) => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
const rupees = (n: number) =>
  `₹${n.toLocaleString("en-IN", { minimumFractionDigits: Number.isInteger(n) ? 0 : 2, maximumFractionDigits: 2 })}`;

interface Company {
  name: string;
  cin: string;
  district: string;
  pin: string | null;
  kind: string;
  size: string;
  registered_year: number | null;
  km: number | null;
}
interface Directory {
  suppliers: Company[];
  total?: number;
  known: boolean;
  source?: string;
  note: string;
}
interface Item {
  id: string;
  category: string;
  quantity: number;
  max_unit_price: number | null;
}
interface Quote {
  id: string;
  name: string;
  category: string;
  unit_price: number;
  max_capacity: number;
  min_order: number;
  district: string;
}
interface Split {
  supplier: string;
  district: string;
  units: number;
  unit_price: number;
  cost: number;
}
interface Plan {
  status: string;
  lines: Array<{ line: string; category: string; quantity: number; splits: Split[]; unmet: number; why_unmet: string[] }>;
  total_cost: number;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.error_message ?? `Request failed (${res.status})`);
  }
  return res.json();
}

function loadSaved(): { items: Item[]; quotes: Quote[] } {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* private window */
  }
  return { items: [], quotes: [] };
}

let counter = Date.now();
const newId = (p: string) => `${p}${(counter++).toString(36)}`;

function Find({ onQuote }: { onQuote: (c: Company, category: string) => void }) {
  const [category, setCategory] = useState("packaging");
  const [district, setDistrict] = useState("");
  const [pin, setPin] = useState("");
  const [out, setOut] = useState<Directory | null>(null);
  const [error, setError] = useState("");

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      setOut(
        await post<Directory>("/api/v1/b2b/directory", {
          category,
          district: district || null,
          pin: /^6\d{5}$/.test(pin) ? pin : null,
          limit: 15,
        }),
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <section>
      <h2>1. Find companies to ask</h2>
      <form onSubmit={run}>
        <p>
          <label htmlFor="sup-cat">What do you need?</label>{" "}
          <select id="sup-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
            {Object.entries(CATEGORIES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>{" "}
          <label htmlFor="sup-district">Near district</label>{" "}
          <select id="sup-district" value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">Anywhere in Tamil Nadu</option>
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {cap(d)}
              </option>
            ))}
          </select>{" "}
          <label htmlFor="sup-pin">or your PIN code</label>{" "}
          <input
            id="sup-pin"
            inputMode="numeric"
            pattern="6[0-9]{5}"
            size={7}
            value={pin}
            onChange={(e) => setPin(e.target.value.trim())}
          />{" "}
          <button type="submit">Find</button>
        </p>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {out ? (
        <>
          {out.suppliers.length ? (
            <>
              <p>
                Showing {out.suppliers.length}
                {out.total ? ` of ${out.total.toLocaleString("en-IN")}` : ""} registered companies, nearest first.
              </p>
              <table>
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Where</th>
                    <th scope="col">Makes or trades</th>
                    <th scope="col">Size</th>
                    <th scope="col">Since</th>
                    <th scope="col">Quote</th>
                  </tr>
                </thead>
                <tbody>
                  {out.suppliers.map((c) => (
                    <tr key={c.cin}>
                      <td>
                        {c.name}
                        <br />
                        <small>CIN {c.cin}</small>
                      </td>
                      <td>
                        {cap(c.district)}
                        {c.pin ? ` ${c.pin}` : ""}
                        {c.km !== null ? ` · about ${Math.round(c.km)} km` : ""}
                      </td>
                      <td>{c.kind === "maker" ? "Makes" : "Trades"}</td>
                      <td>{cap(c.size)}</td>
                      <td>{c.registered_year ?? "?"}</td>
                      <td>
                        <button type="button" onClick={() => onQuote(c, category)}>
                          I got a quote
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p>No registered company found for this.</p>
          )}
          <p>
            <small>
              {out.note} {out.source ?? ""}
            </small>
          </p>
        </>
      ) : null}
    </section>
  );
}

export default function Suppliers() {
  const [items, setItems] = useState<Item[]>(() => loadSaved().items);
  const [quotes, setQuotes] = useState<Quote[]>(() => loadSaved().quotes);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify({ items, quotes }));
    } catch {
      /* the page still works; it just will not remember */
    }
  }, [items, quotes]);

  const addQuote = (c?: Company, category = "packaging") =>
    setQuotes((q) => [
      ...q,
      {
        id: newId("q"),
        name: c?.name ?? "",
        category,
        unit_price: 0,
        max_capacity: 0,
        min_order: 1,
        district: c?.district ?? "",
      },
    ]);
  const setQuote = (id: string, patch: Partial<Quote>) =>
    setQuotes((q) => q.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  const setItem = (id: string, patch: Partial<Item>) =>
    setItems((l) => l.map((x) => (x.id === id ? { ...x, ...patch } : x)));

  const ready = items.filter((i) => i.quantity > 0);
  const usable = quotes.filter((q) => q.name && q.unit_price > 0 && q.max_capacity > 0);

  const run = async () => {
    setError("");
    try {
      setPlan(
        await post<Plan>("/api/v1/b2b/allocate", {
          lines: ready.map((i) => ({
            id: i.id,
            category: i.category,
            quantity: i.quantity,
            max_unit_price: i.max_unit_price || null,
          })),
          quotes: usable,
        }),
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const itemName = (id: string) => {
    const i = items.find((x) => x.id === id);
    return i ? CATEGORIES[i.category] ?? i.category : id;
  };

  return (
    <section>
      <h1>Suppliers</h1>
      <p>
        Find real Tamil Nadu companies to ask for quotes, then plan each month's order across the quotes you
        receive.
      </p>

      <Find
        onQuote={(c, category) => {
          addQuote(c, category);
          document.getElementById("quotes")?.scrollIntoView();
        }}
      />

      <hr />
      <h2>2. Plan your monthly order</h2>
      <h3>What you need each month</h3>
      {items.map((i) => (
        <p key={i.id}>
          <select
            aria-label="Item"
            value={i.category}
            onChange={(e) => setItem(i.id, { category: e.target.value })}
          >
            {Object.entries(CATEGORIES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>{" "}
          <label>
            units a month{" "}
            <input
              type="number"
              min={1}
              value={i.quantity || ""}
              onChange={(e) => setItem(i.id, { quantity: Number(e.target.value) })}
            />
          </label>{" "}
          <label>
            most you can pay per unit (₹, optional){" "}
            <input
              type="number"
              min={0}
              step="0.01"
              value={i.max_unit_price ?? ""}
              onChange={(e) => setItem(i.id, { max_unit_price: e.target.value ? Number(e.target.value) : null })}
            />
          </label>{" "}
          <button type="button" onClick={() => setItems((l) => l.filter((x) => x.id !== i.id))}>
            Remove
          </button>
        </p>
      ))}
      <p>
        <button
          type="button"
          onClick={() =>
            setItems((l) => [...l, { id: newId("i"), category: "packaging", quantity: 0, max_unit_price: null }])
          }
        >
          Add an item
        </button>
      </p>

      <h3 id="quotes">Quotes you received</h3>
      {quotes.map((q) => (
        <p key={q.id}>
          <input
            aria-label="Supplier name"
            placeholder="Supplier name"
            value={q.name}
            onChange={(e) => setQuote(q.id, { name: e.target.value })}
          />{" "}
          <select
            aria-label="For item"
            value={q.category}
            onChange={(e) => setQuote(q.id, { category: e.target.value })}
          >
            {Object.entries(CATEGORIES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>{" "}
          <label>
            ₹ per unit{" "}
            <input
              type="number"
              min={0}
              step="0.01"
              value={q.unit_price || ""}
              onChange={(e) => setQuote(q.id, { unit_price: Number(e.target.value) })}
            />
          </label>{" "}
          <label>
            can supply a month{" "}
            <input
              type="number"
              min={1}
              value={q.max_capacity || ""}
              onChange={(e) => setQuote(q.id, { max_capacity: Number(e.target.value) })}
            />
          </label>{" "}
          <label>
            minimum order{" "}
            <input
              type="number"
              min={1}
              value={q.min_order}
              onChange={(e) => setQuote(q.id, { min_order: Math.max(1, Number(e.target.value)) })}
            />
          </label>{" "}
          <button type="button" onClick={() => setQuotes((l) => l.filter((x) => x.id !== q.id))}>
            Remove
          </button>
        </p>
      ))}
      <p>
        <button type="button" onClick={() => addQuote()}>
          Add a quote
        </button>
      </p>

      <p>
        <button type="button" onClick={() => void run()} disabled={!ready.length || !usable.length}>
          Split the order
        </button>{" "}
        {!ready.length ? "Add what you need first." : !usable.length ? "Add at least one quote with a price and capacity." : ""}
      </p>
      {error ? <p role="alert">{error}</p> : null}

      {plan ? (
        <>
          <h3>The plan</h3>
          {plan.lines.map((l) => (
            <div key={l.line}>
              <h4>
                {itemName(l.line)}: {l.quantity.toLocaleString("en-IN")} a month
              </h4>
              {l.splits.length ? (
                <ul>
                  {l.splits.map((s) => (
                    <li key={s.supplier}>
                      {s.units.toLocaleString("en-IN")} from {s.supplier}
                      {s.district ? ` (${cap(s.district)})` : ""} at {rupees(s.unit_price)}: {rupees(s.cost)}
                    </li>
                  ))}
                </ul>
              ) : null}
              {l.unmet ? (
                <p>
                  <strong>{l.unmet.toLocaleString("en-IN")} not covered:</strong>{" "}
                  {l.why_unmet.length ? `${cap(l.why_unmet.join("; "))}.` : ""}
                </p>
              ) : null}
            </div>
          ))}
          <p>Monthly cost of what is covered: {rupees(plan.total_cost)}</p>
        </>
      ) : null}
    </section>
  );
}
