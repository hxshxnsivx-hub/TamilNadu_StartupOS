import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth";
import { Page, Threshold } from "../design/atelier";

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
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
      await login(email, password);
      nav("/app");
    } catch (ex: any) {
      setErr(ex.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page set="account" className="v-authpage">
      <Threshold
        eyebrow="Tamil Nadu StartupOS"
        title={t("login")}
        note={t("tagline")}
      >
        <form className="v-form" onSubmit={submit}>
          {/* the error sits with the field it concerns, not stacked at the top */}
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
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <button className="btn primary" disabled={busy}>
            {busy ? t("loading") : t("login")}
          </button>

          <p className="v-note v-thr-foot">
            {t("no_account")} <Link to="/register">{t("register")}</Link>
          </p>
        </form>
      </Threshold>
    </Page>
  );
}
