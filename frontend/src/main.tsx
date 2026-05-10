// ─────────────────────────────────────────────────────────
// main.tsx
// Entry point. Providers in order:
//   BrowserRouter → QueryClientProvider → App
//
// React Query v3 defaults:
//   - retry: 1 (avoids hammering a cold API)
//   - refetchOnWindowFocus: false (data is pre-computed;
//     no need to re-fetch on tab switch)
// ─────────────────────────────────────────────────────────

import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
)