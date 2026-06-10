import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Proxy all /api/v1 requests to the FastAPI backend.
    // This runs both origins on the same host from the browser's perspective,
    // so CORS headers are never needed for local development.
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8085',
        changeOrigin: false,
        secure: false,
        ws: true,          // proxy WebSocket upgrade requests too
        rewrite: (path) => path,  // keep path as-is
      },
    },
  },
})


