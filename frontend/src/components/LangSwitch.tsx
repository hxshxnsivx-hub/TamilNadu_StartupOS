import { useTranslation } from "react-i18next";

/* EN / தமிழ் / हिंदी are first-class here, not a translation layer bolted on
   afterwards — so the switch sits in the masthead at full size rather than
   hiding in a footer dropdown. */
const LANGS = [
  { code: "en", label: "EN" },
  { code: "ta", label: "தமிழ்" },
  { code: "hi", label: "हिंदी" },
];

export default function LangSwitch() {
  const { i18n } = useTranslation();

  // i18n.language can carry a region suffix (e.g. "en-GB") — match on the base
  // tag so the indicator never falls off the end of the switch.
  const base = (i18n.language || "en").split("-")[0];
  const active = Math.max(
    0,
    LANGS.findIndex((l) => l.code === base),
  );

  return (
    <div className="v-lang" role="group" aria-label="Language">
      {/* the lit key — a slab of pigment that slides under the active label */}
      <span
        className="v-lang-ind"
        style={{ "--i": active } as React.CSSProperties}
        aria-hidden="true"
      />
      {LANGS.map((l) => (
        <button
          key={l.code}
          type="button"
          aria-pressed={base === l.code}
          className={base === l.code ? "is-on" : ""}
          onClick={() => {
            i18n.changeLanguage(l.code);
            localStorage.setItem("vanigam_lang", l.code);
          }}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
