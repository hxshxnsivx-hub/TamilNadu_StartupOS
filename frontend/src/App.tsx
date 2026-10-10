import { Link, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LangSwitch from "./components/LangSwitch";
import { useAuth } from "./auth";
import { ScrollRail, useStuck } from "./motion";
import Wall from "./components/Wall";
import AmbientBackground from "./components/layout/AmbientBackground";
import { MotionProvider } from "./components/motion";
import Home from "./pages/Home";
import Start from "./pages/Start";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Consent from "./pages/Consent";
import Ideate from "./pages/Ideate";
import Talk from "./pages/Talk";
import Schemes from "./pages/Schemes";
import B2B from "./pages/B2B";
import Supply from "./pages/Supply";
import Funding from "./pages/Funding";
import Pipeline from "./pages/Pipeline";
import Intel from "./pages/Intel";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "navlink is-active" : "navlink";

/* The primary run, in the order a founder actually hits it. Secondary
   surfaces (supply, pipeline, consent) are reached from the page they belong
   to rather than crowding the masthead — an overloaded nav is a nav nobody
   reads. */
const NAV = [
  { to: "/ideate", key: "ideate_nav" },
  { to: "/talk", label: "Talk" },
  { to: "/schemes", key: "schemes" },
  { to: "/b2b", key: "b2b" },
  { to: "/funding", key: "funding" },
];

function Nav() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const stuck = useStuck();
  return (
    <header className={stuck ? "nav is-stuck" : "nav"}>
      <Link to="/" className="brand">
        Vanigam <b lang="ta">வணிகம்</b>
      </Link>
      <div className="nav-right">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} className={linkClass}>
            {t(n.key)}
          </NavLink>
        ))}
        <NavLink to="/intel" className={linkClass}>
          Intel
        </NavLink>
        <LangSwitch />
        {user ? (
          <>
            <Link to="/app" className="btn ghost">
              {t("welcome")}
            </Link>
            <Link to="/profile" className="btn ghost">
              {t("profile")}
            </Link>
            <button className="btn ghost" onClick={logout}>
              {t("sign_out")}
            </button>
          </>
        ) : (
          <Link to="/login" className="btn ghost">
            {t("sign_in")}
          </Link>
        )}
      </div>
    </header>
  );
}

function Protected({ children }: { children: JSX.Element }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="center muted">…</div>;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const location = useLocation();
  return (
    <MotionProvider>
    <div className="app">
      {/* The wall carries the palette and the only continuous motion in the
          product. It sits behind everything, fixed, and holds no information —
          so when reduced-motion stops it, nothing is lost but the movement. */}
      <Wall />
      {/* Rendered AFTER Wall deliberately: both sit at z-0, so DOM order puts
          the ambient texture on top of the wall while both stay behind .app
          (z-1). Carries the per-route accent hue. */}
      <AmbientBackground />
      <ScrollRail />
      <Nav />
      {/* keyed on pathname so every route change replays the entrance cut */}
      <main key={location.pathname}>
        <Routes location={location}>
          <Route path="/" element={<Home />} />
          <Route path="/start" element={<Start />} />
          <Route path="/ideate" element={<Ideate />} />
          <Route path="/talk" element={<Talk />} />
          <Route path="/schemes" element={<Schemes />} />
          <Route path="/b2b" element={<B2B />} />
          <Route path="/supply" element={<Supply />} />
          <Route path="/funding" element={<Funding />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/intel" element={<Intel />} />
          <Route path="/consent" element={<Consent />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/app"
            element={
              <Protected>
                <Dashboard />
              </Protected>
            }
          />
          <Route
            path="/profile"
            element={
              <Protected>
                <Profile />
              </Protected>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
    </MotionProvider>
  );
}
