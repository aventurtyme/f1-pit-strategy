// ─────────────────────────────────────────────────────────
// App.tsx
// Root layout: NavBar (sticky) + routed content area.
// Phase 5 routes (Teams, Circuits, Insights) are stubbed
// with placeholder pages so NavBar links are functional.
// ─────────────────────────────────────────────────────────

import { Routes, Route } from 'react-router-dom'
import { TeamView }    from './views/TeamView'
import { CircuitView } from './views/CircuitView'
import { InsightsPanel } from './components/insights/InsightsPanel'
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
          <Route path="/"                      element={<TimelineView />} />
          <Route path="/teams/:team"           element={<TeamView />} />
          <Route path="/circuits/:circuitKey"  element={<CircuitView />} />
          <Route path="/insights"              element={<InsightsPanel />} />
          <Route path="*"                      element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}