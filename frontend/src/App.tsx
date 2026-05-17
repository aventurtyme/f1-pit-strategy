// ─────────────────────────────────────────────────────────
// App.tsx
// Root layout: sticky NavBar + routed content area.
// Phase 5 views are now live — no more stubs.
//
// Route structure (matches layout_proposal.html tab names):
//   /             → TimelineView
//   /teams        → TeamsView   (self-contained season + team selector)
//   /circuits     → CircuitsView (self-contained season + circuit list)
//   /insights     → InsightsView
//   *             → NotFound
// ─────────────────────────────────────────────────────────

import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import TimelineView from './views/TimelineView'
import { TeamsView }    from './views/TeamsView'
import { CircuitsView } from './views/CircuitsView'
import { InsightsView } from './views/InsightsView'
import NotFound from './views/NotFound'
import styles from './App.module.css'

export default function App() {
  return (
    <div className={styles.root}>
      <NavBar />
      <main className={styles.main}>
        <Routes>
          <Route path="/"          element={<TimelineView />} />
          <Route path="/teams"     element={<TeamsView />} />
          <Route path="/circuits"  element={<CircuitsView />} />
          <Route path="/insights"  element={<InsightsView />} />
          <Route path="*"          element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}