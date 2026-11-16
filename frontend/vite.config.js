import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In dev, /api is proxied to the FastAPI backend, so the browser never needs CORS and no key ever reaches the client.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: {
    // The three.js chunk (~920 kB, ~245 kB gzipped) is lazy-loaded after first paint, so it doesn't block the UI.
    chunkSizeWarningLimit: 1000,
  },
})
