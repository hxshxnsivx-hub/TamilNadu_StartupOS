import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

// nocturne first (it owns the reset and the hand-written components), theme
// second so Tailwind utilities win same-specificity ties against it.
import "./nocturne.css";
import "./theme.css";
import App from "./App";
import { AuthProvider } from "./auth";
import "./i18n";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {/* Opt into both v7 behaviours now rather than at the upgrade. Route
        changes wrap in startTransition (which also keeps the scroll-driven
        scenes from janking on navigation), and splat routes resolve relative
        paths the v7 way — this app has a catch-all "*" route, so that one
        would have changed behaviour under us. */}
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
