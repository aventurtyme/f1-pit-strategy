// ─────────────────────────────────────────────────────────
// App.tsx
// Root layout: NavBar (sticky) + routed content area.
// Phase 5 routes (Teams, Circuits, Insights) are stubbed
// with placeholder pages so NavBar links are functional.
// ─────────────────────────────────────────────────────────

import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import TimelineView from './views/TimelineView'
import NotFound from './views/NotFound'
import styles from './App.module.css'

// ── Phase 5 stubs — replaced in next phase ───────────────
function ComingSoon({ name }: { name: string }) {
  return (
    <div className={styles.comingSoon}>
      <p>{name} view — Phase 5</p>
    </div>
  )
}

export default function App() {
  return (
    <div className={styles.root}>
      <NavBar />
      <main className={styles.main}>
        <Routes>
          <Route path="/"          element={<TimelineView />} />
          <Route path="/teams"     element={<ComingSoon name="Teams" />} />
          <Route path="/circuits"  element={<ComingSoon name="Circuits" />} />
          <Route path="/insights"  element={<ComingSoon name="Insights" />} />
          <Route path="*"          element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}