import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

// Dev server on 5173 (NOT 3000). /api and /health proxy to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  // "@/…" → src/…, mirroring tsconfig paths so both resolvers agree.
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
