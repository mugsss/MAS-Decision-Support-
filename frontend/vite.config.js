import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // FastAPI serves this directory in production.
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // Dev server proxies API calls to the FastAPI backend so the frontend
    // can be developed with hot reload against the live agents.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
