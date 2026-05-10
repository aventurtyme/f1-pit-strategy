// ─────────────────────────────────────────────────────────
// api/client.ts
// Single Axios instance. All requests go through the Vite
// proxy at /api, which strips the prefix before forwarding
// to FastAPI on localhost:8000.
// ─────────────────────────────────────────────────────────

import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  // Reasonable timeout for pre-computed reads (<300ms P95 target)
  timeout: 10_000,
})

export default client