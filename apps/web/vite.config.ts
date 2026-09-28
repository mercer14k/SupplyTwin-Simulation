import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": process.env.SUPPLYTWIN_API_TARGET || "http://127.0.0.1:8000",
      "/docs": process.env.SUPPLYTWIN_API_TARGET || "http://127.0.0.1:8000",
      "/openapi.json":
        process.env.SUPPLYTWIN_API_TARGET || "http://127.0.0.1:8000",
      "/health": process.env.SUPPLYTWIN_API_TARGET || "http://127.0.0.1:8000",
    },
  },
});
