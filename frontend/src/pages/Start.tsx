import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Band,
  Choice,
  Masthead,
  Page,
  Setting,
  Shelf,
  Stepper,
  Uncover,
} from "../design/atelier";
import {
  ENTRY_MODES,
  REG_SUBTYPES,
  TERRAINS,
  classifyTerrain,
  loadJourney,
  saveJourney,
  type EntryMode,
  type Journey,
  type RegSubtype,
  type Terrain,
} from "../journeyStore";

/* The front door.
 *
 * Two questions set two enums, and those two enums route everything
 * downstream — which schemes are even checked, which journey the roadmap
 * describes, which readiness axes matter. Asking them once, here, is the
 * difference between a product and four disconnected tools.
 *
 * The third step is a confirmation, not a question: terrain is inferred from
 * the first two and shown for the founder to accept or change. A classifier
 * that cannot be argued with quietly mis-serves everyone it gets wrong. */

const STEPS = ["Where you are", "What exists", "Confirm"];

export default function Start() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [j, setJ] = useState<Journey>(() => loadJourney());
  const [step, setStep] = useState(0);

  // terrain follows the two enums until the founder overrides it, at which
  // point their choice wins and re-classification stops
  useEffect(() => {
    if (j.terrain_confirmed) return;
    const guess = classifyTerrain(j.entry_mode, j.reg_subtype);
    if (guess !== j.terrain) setJ((x) => ({ ...x, terrain: guess }));
  }, [j.entry_mode, j.reg_subtype, j.terrain, j.terrain_confirmed]);

  const setMode = (v: string) =>
    setJ((x) => ({ ...x, entry_mode: v as EntryMode }));
  const setSub = (v: string) =>
    setJ((x) => ({ ...x, reg_subtype: v as RegSubtype }));
  const setTerrain = (v: string) =>
    setJ((x) => ({ ...x, terrain: v as Terrain, terrain_confirmed: true }));

  const canAdvance =
    (step === 0 && !!j.entry_mode) ||
    (step === 1 && !!j.reg_subtype) ||
    (step === 2 && !!j.terrain);

  function finish() {
    saveJourney({ ...j, terrain_confirmed: true });
    // where the founder lands depends on how they arrived — that is the whole
    // point of asking. An idea goes to be tested; no idea goes to discovery.
    nav(j.entry_mode === "idea" ? "/ideate" : "/schemes");
  }

  const terrainMeta = TERRAINS.find((x) => x.id === j.terrain);

  return (
    <Page set="ideate">
      <Masthead
        index="Start here"
        lines={[t("start_title")]}
        lede={t("start_lede")}
      />

      <Band depth={3} tone="work">
        <Stepper steps={STEPS} at={step} />

        {step === 0 && (
          <fieldset className="v-fieldset v-choices">
            <legend>Where you are</legend>
            <div className="v-choicegrid" role="radiogroup">
              {ENTRY_MODES.map((m, i) => (
                <Choice
                  key={m.id}
                  name="entry_mode"
                  value={m.id}
                  checked={j.entry_mode === m.id}
                  onChange={setMode}
                  label={m.label}
                  ta={m.ta}
                  body={m.body}
                  index={i}
                />
              ))}
            </div>
          </fieldset>
        )}

        {step === 1 && (
          <fieldset className="v-fieldset v-choices">
            <legend>What already exists</legend>
            <div className="v-choicegrid" role="radiogroup">
              {REG_SUBTYPES.map((s, i) => (
                <Choice
                  key={s.id}
                  name="reg_subtype"
                  value={s.id}
                  checked={j.reg_subtype === s.id}
                  onChange={setSub}
                  label={s.label}
                  ta={s.ta}
                  body={s.body}
                  index={i}
                />
              ))}
            </div>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset className="v-fieldset v-choices">
            <legend>Confirm your terrain</legend>

            <Uncover>
              <p className="v-aside">
                From those two answers we read you as{" "}
                <b className="v-path">{terrainMeta?.label ?? "—"}</b>
                {terrainMeta ? ` — ${terrainMeta.body}` : ""} This is a guess, and
                it changes which scheme families are checked. If it is wrong,
                change it.
              </p>
            </Uncover>

            <div className="v-choicegrid" role="radiogroup">
              {TERRAINS.map((tr, i) => (
                <Choice
                  key={tr.id}
                  name="terrain"
                  value={tr.id}
                  checked={j.terrain === tr.id}
                  onChange={setTerrain}
                  label={tr.label}
                  body={tr.body}
                  index={i}
                />
              ))}
            </div>
          </fieldset>
        )}

        <Shelf
          note={
            step < 2
              ? `Step ${step + 1} of ${STEPS.length}`
              : j.terrain_confirmed
                ? "Overridden by you"
                : "Auto-classified"
          }
        >
          {step > 0 && (
            <button className="btn ghost" onClick={() => setStep((s) => s - 1)}>
              Back
            </button>
          )}
          {step < 2 ? (
            <button
              className="btn primary"
              disabled={!canAdvance}
              onClick={() => setStep((s) => s + 1)}
            >
              Continue
            </button>
          ) : (
            <button className="btn primary" disabled={!canAdvance} onClick={finish}>
              {t("get_started")}
            </button>
          )}
        </Shelf>
      </Band>

      <Band depth={3}>
        <div className="v-split">
          <Setting
            as="h2"
            className="v-pull"
            lines={["Skip this if", "you would rather."]}
          />
          <div className="v-stack">
            <p className="v-aside">
              Every tool works without answering anything. These two questions
              only make the results narrower and more accurate — they are not a
              gate.
            </p>
            <div className="v-row">
              <Link to="/schemes" className="btn ghost">
                {t("schemes")}
              </Link>
              <Link to="/ideate" className="btn ghost">
                {t("ideate_nav")}
              </Link>
            </div>
          </div>
        </div>
      </Band>
    </Page>
  );
}
