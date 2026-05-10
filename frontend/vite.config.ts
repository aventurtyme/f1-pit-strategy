import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        // All /api/* requests are forwarded to the FastAPI backend.
        // Override VITE_API_TARGET in .env to change the backend port.
        '/api': {
          target: env.VITE_API_TARGET ?? 'http://localhost:8000',
          changeOrigin: true,
          // Strip the /api prefix — FastAPI routes are at /seasons, /races, etc.
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})