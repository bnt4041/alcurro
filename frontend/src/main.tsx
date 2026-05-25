import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { applyAlcurroDefaults } from "./hooks/useBranding";
import "./index.css";
import "./styles/tabulator-theme.css";

applyAlcurroDefaults();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
