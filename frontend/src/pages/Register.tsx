import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth";
import { Page, Threshold } from "../design/atelier";

export default function Register() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await register(email, password);
      nav("/app");
    } catch (ex: any) {
      setErr(ex.message || "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page set="account" className="v-authpage">
      <Threshold
        eyebrow="Tamil Nadu StartupOS"
        title={t("register")}
        note={t("tagline")}
      >
        <form className="v-form" onSubmit={submit}>
          {err && (
            <div className="v-err" role="alert">
              {err}
            </div>
          )}

          <label className="v-fld">
            <span>{t("email")}</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="v-fld">
            <span>{t("password")}</span>
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
            {/* the rule is stated before it can be broken, not after */}
            <small className="v-hint">Minimum 8 characters</small>
          </label>

          <button className="btn primary" disabled={busy}>
            {busy ? t("loading") : t("register")}
          </button>

          <p className="v-note v-thr-foot">
            {t("have_account")} <Link to="/login">{t("login")}</Link>
          </p>
        </form>
      </Threshold>
    </Page>
  );
}
