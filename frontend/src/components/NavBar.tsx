// ─────────────────────────────────────────────────────────
// components/NavBar.tsx
// Nav links go to route roots — no hardcoded team/circuit.
// Season + race selectors only appear on the Timeline route;
// other views manage their own season controls internally.
// ─────────────────────────────────────────────────────────

import { NavLink, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { useSeasons, useRaces } from '../api/queries'
import useUiStore from '../store/uiStore'
import styles from './NavBar.module.css'

const NAV_ITEMS = [
  { path: '/',         label: 'Timeline' },
  { path: '/teams',    label: 'Teams'    },
  { path: '/circuits', label: 'Circuits' },
  { path: '/insights', label: 'Insights' },
]

export default function NavBar() {
  const location = useLocation()
  const isTimeline = location.pathname === '/'

  const { selectedSeason, selectedSessionId, setSeason, setSessionId } = useUiStore()
  const { data: seasons } = useSeasons()
  const { data: races }   = useRaces(selectedSeason)

  // ── Hydrate store from localStorage on first mount ─────
  useEffect(() => {
    const stored = localStorage.getItem('pit-analyzer-ui')
    if (stored) {
      try {
        const { season, sessionId } = JSON.parse(stored)
        if (season && !selectedSeason)       setSeason(season)
        if (sessionId && !selectedSessionId) setSessionId(sessionId)
      } catch { /* ignore */ }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Persist to localStorage ────────────────────────────
  useEffect(() => {
    localStorage.setItem(
      'pit-analyzer-ui',
      JSON.stringify({ season: selectedSeason, sessionId: selectedSessionId })
    )
  }, [selectedSeason, selectedSessionId])

  return (
    <nav className={styles.nav} aria-label="Main navigation">
      <span className={styles.brand}>Pit Analyzer</span>

      <div className={styles.links}>
        {NAV_ITEMS.map(({ path, label }) => (
          <NavLink
            key={label}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.active : ''}`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>

      {/* Race selectors — Timeline only */}
      {isTimeline && (
        <div className={styles.selectors}>
          <select
            className={styles.select}
            value={selectedSeason ?? ''}
            onChange={e => setSeason(e.target.value ? Number(e.target.value) : null)}
            aria-label="Select season"
          >
            <option value="" disabled>Season</option>
            {seasons?.map(s => (
              <option key={s.season} value={s.season}>
                {s.season} Season
              </option>
            ))}
          </select>

          <select
            className={styles.select}
            value={selectedSessionId ?? ''}
            onChange={e => setSessionId(e.target.value || null)}
            disabled={!races?.length}
            aria-label="Select race"
          >
            <option value="" disabled>
              {selectedSeason ? 'Select race' : '— select season first —'}
            </option>
            {races?.map(r => (
              <option key={r.id} value={r.id}>
                Rd {String(r.round).padStart(2, '0')} — {r.circuit_name}
              </option>
            ))}
          </select>
        </div>
      )}
    </nav>
  )
}