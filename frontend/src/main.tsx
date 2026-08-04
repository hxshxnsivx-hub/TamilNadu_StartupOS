import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

/* Cascade order is load-bearing — later sheets settle ties against earlier
   ones, and each layer has one job:
     index.css        base reset, and the legacy page layout still in use
     meridian.css     the theme: ground, ink, signal, brass, surfaces, type
     meridian-motion  the older motion grammar (Reveal, ScrollRail, kolam)
     design/tokens    the canonical token set — space ladder, corner ladder,
                      pigment names, opacity ceilings, motion vocabulary
     design/wall      the background, which is a composed surface not a colour
     design/atelier   structure: the primitives every page is now built from
     design/composit. page-specific arrangements of those primitives
   The retired "Gilded Pigment" sheets (luxe.css, motion.css) and the retired
   landing sheet (styles/home.css) are not imported anywhere. */
import "./index.css";
import App from "./App";
import { AuthProvider } from "./auth";
import "./i18n";
import "./meridian.css";
import "./meridian-motion.css";
import "./design/tokens.css";
import "./design/wall.css";
import "./design/atelier.css";
import "./design/compositions.css";
import "./design/surfaces.css";
import "./design/signature.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
