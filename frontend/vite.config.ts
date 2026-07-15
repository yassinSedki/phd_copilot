import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    watch: {
      // File-change events don't propagate to WSL for projects on /mnt/*
      // (Windows-mounted drives), so HMR silently stops working there.
      // Polling catches every change regardless of where the edit came from.
      usePolling: true,
      interval: 300,
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
