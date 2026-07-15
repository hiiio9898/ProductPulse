import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      // 开发环境代理后端 API
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});