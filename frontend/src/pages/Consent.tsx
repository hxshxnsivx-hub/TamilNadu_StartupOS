import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, type VerificationOut } from "../api";
import {
  Band,
  Masthead,
  Page,
  Plate,
  PlateHead,
  Provenance,
  Reasons,
  Shelf,
  Uncover,
} from "../design/atelier";
import { loadJourney, saveJourney } from "../journeyStore";

/* Consent and legal verification, on one surface.
 *
 * Two rules from the spec shape this screen, and both are the kind that get
 * quietly dropped when a deadline approaches:
 *
 *  1. Consent is PER PURPOSE. There is no blanket "I agree" here, because
 *     caste category and financial capacity are a protected class with their
 *     own purpose limitation — bundling them into one checkbox with analytics
 *     would make the whole consent unusable as a record.
 *
 *  2. Identifiers are never echoed. The verification endpoint returns a masked
 *     value, and this screen keeps the raw number only in the input the
 *     founder is typing into. Nothing is written to storage.
 */

const PURPOSES = [
  {
    id: "core",
    label: "Run the platform for me",
    body: "Profile, roadmap, and scheme matching. Without this nothing on the platform can produce a result.",
    required: true,
  },
  {
    id: "caste",
    label: "Use my caste category for reserved-category schemes",
    body: "Checked only against reserved-category eligibility rules. Never shown to partners, suppliers or investors, and never used for ranking anything else.",
    required: false,
  },
  {
    id: "financial",
    label: "Use my declared financial capacity",
    body: "Used to filter opportunities to ones you could actually fund. Held in the same protected class as caste category.",
    required: false,
  },
  {
    id: "idea_ip",
    label: "Show my unregistered idea in match results",
    body: "Your idea is masked in partner match cards until both sides accept. Declining keeps it entirely private, and matching still works — it just has less to go on.",
    required: false,
    legal: true,
  },
  {
    id: "digest",
    label: "Send me a weekly digest",
    body: "Scheme deadlines, new matches, policy changes. In-app first, then email, then SMS.",
    required: false,
  },
];

const KINDS = [
  { id: "cin", label: "CIN", hint: "Company Identification Number, 21 characters" },
  { id: "gstin", label: "GSTIN", hint: "15-character GST identifier" },
  { id: "pan", label: "PAN", hint: "10-character permanent account number" },
  { id: "dpiit", label: "DPIIT", hint: "Startup India recognition number" },
];

export default function Consent() {
  const { t } = useTranslation();
  const [j, setJ] = useState(() => loadJourney());
  const [saved, setSaved] = useState(false);

  const [kind, setKind] = useState("cin");
  const [value, setValue] = useState("");
  const [result, setResult] = useState<VerificationOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function toggle(id: string, on: boolean) {
    setSaved(false);
    setJ((x) => ({ ...x, consent: { ...x.consent, [id]: on } }));
  }

  function persist() {
    saveJourney(j);
    setSaved(true);
  }

  async function verify() {
    setErr(null);
    setBusy(true);
    setResult(null);
    try {
      setResult(await api.verify(kind, value.trim()));
      // the raw identifier is cleared the moment it has been checked — this
      // screen has no reason to keep holding it
      setValue("");
    } catch (e: any) {
      setErr(e.message || "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  const active = KINDS.find((k) => k.id === kind);
  const granted = PURPOSES.filter((p) => j.consent[p.id] || p.required).length;

  return (
    <Page set="account">
      <Masthead
        index="Consent & verification"
        lines={[t("consent_title")]}
        lede={t("consent_lede")}
      />

      <Band
        depth={3}
        tone="work"
        folio="I"
        title={["Purposes"]}
        index={`${granted} of ${PURPOSES.length} granted`}
      >
        <div className="v-consent">
          {PURPOSES.map((p) => {
            const on = p.required || !!j.consent[p.id];
            return (
              <label
                key={p.id}
                className={[
                  "v-purpose",
                  on && "is-on",
                  p.required && "is-required",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <input
                  type="checkbox"
                  checked={on}
                  disabled={p.required}
                  onChange={(e) => toggle(p.id, e.target.checked)}
                />
                <span className="v-purpose-body">
                  <span className="v-purpose-l">
                    {p.label}
                    {p.required && <span className="v-tag is-quiet">required</span>}
                    {p.legal && <span className="v-tag">legal notice</span>}
                  </span>
                  <span className="v-purpose-d">{p.body}</span>
                  {p.legal && (
                    <span className="v-purpose-legal">
                      An unregistered idea has no statutory IP protection. Sharing
                      it here — masked or not — is not a substitute for filing,
                      and this platform makes no claim to own or defend it.
                    </span>
                  )}
                </span>
                <i className="v-purpose-edge" aria-hidden="true" />
              </label>
            );
          })}
        </div>

        <Shelf note={saved ? "Saved in this browser" : "Not saved yet"}>
          <button className="btn primary" onClick={persist}>
            Save these choices
          </button>
        </Shelf>
      </Band>

      <Band
        depth={3}
        tone="statement"
        folio="II"
        title={["Verify a legal identifier"]}
        index="CIN · GSTIN · PAN · DPIIT"
      >
        <Uncover>
          <p className="v-aside">
            Verification is what turns a claimed company into a checkable one,
            and several schemes will not consider an unverified entity at all.
            The number you type is sent once, checked, and cleared — only a
            masked form is ever returned or shown.
          </p>
        </Uncover>

        <div className="v-form">
          <fieldset className="v-fieldset">
            <legend>Identifier</legend>
            <div className="v-grid2">
              <label className="v-fld">
                <span>Kind</span>
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  {KINDS.map((k) => (
                    <option key={k.id} value={k.id}>
                      {k.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="v-fld">
                <span>{active?.label} number</span>
                <input
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                />
                <small className="v-hint">{active?.hint}</small>
              </label>
            </div>
          </fieldset>

          <Shelf note="Not stored — checked and discarded">
            <button
              className="btn primary"
              onClick={verify}
              disabled={busy || value.trim().length < 3}
            >
              {busy ? "Checking" : "Verify"}
            </button>
          </Shelf>

          {err && (
            <div className="v-err" role="alert">
              {err}
            </div>
          )}
        </div>

        {result && (
          <div className="v-grid">
            <Plate
              tone={
                result.verified ? "var(--oxide-green)" : "var(--oxide-mustard)"
              }
              off={!result.verified}
            >
              <PlateHead
                eyebrow={
                  <>
                    <span className="v-tag">{result.kind.toUpperCase()}</span>
                    <span className="v-tag is-quiet">{result.status}</span>
                  </>
                }
                title={result.value_masked}
                meta={
                  result.verified
                    ? "Checked and confirmed."
                    : "Not confirmed. This is not a rejection of your company — it is a statement about what could be checked."
                }
              />

              {result.reason && (
                <Reasons
                  label="why"
                  items={[result.reason]}
                  refusal={!result.verified}
                />
              )}

              <Provenance>source · {result.source}</Provenance>
            </Plate>
          </div>
        )}
      </Band>

      <Band depth={3}>
        <Uncover>
          <p className="v-aside">
            You can change any of this later. Withdrawing a purpose stops it
            being used from that moment — it does not delete work already done
            under it, and the platform will tell you which results were affected
            rather than silently re-ranking them.{" "}
            <Link to="/profile">Back to your profile</Link>
          </p>
        </Uncover>
      </Band>
    </Page>
  );
}
