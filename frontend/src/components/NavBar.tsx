// ─────────────────────────────────────────────────────────
// components/NavBar.tsx
// Season dropdown uses `s.season` as value.
// Race dropdown uses `r.id` as session_id (not session_id field —
// the backend Race schema uses `id` as the primary key).
// ─────────────────────────────────────────────────────────

import { NavLink, useSearchParams } from 'react-router-dom'
import { useEffect } from 'react'
import { useSeasons, useRaces } from '../api/queries'
import useUiStore from '../store/uiStore'
import styles from './NavBar.module.css'

const navItems = [
  { path: '/',                           label: 'Timeline' },
  { path: '/teams/Ferrari?season=2024',  label: 'Teams'    },
  { path: '/circuits/bahrain',           label: 'Circuits' },
  { path: '/insights',                   label: 'Insights' },
]

export default function NavBar() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { selectedSeason, selectedSessionId, setSeason, setSessionId } = useUiStore()

  const { data: seasons } = useSeasons()
  const { data: races }   = useRaces(selectedSeason)

  // ── Hydrate store from URL on first mount ──────────────
  useEffect(() => {
    const urlSeason    = searchParams.get('season')
    const urlSessionId = searchParams.get('session')
    if (urlSeason && !selectedSeason)       setSeason(Number(urlSeason))
    if (urlSessionId && !selectedSessionId) setSessionId(urlSessionId)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Sync store → URL ───────────────────────────────────
  useEffect(() => {
    const next: Record<string, string> = {}
    if (selectedSeason)    next['season']  = String(selectedSeason)
    if (selectedSessionId) next['session'] = selectedSessionId
    setSearchParams(next, { replace: true })
  }, [selectedSeason, selectedSessionId, setSearchParams])

  return (
    <nav className={styles.nav} aria-label="Main navigation">
      <span className={styles.brand}>Pit Analyzer</span>

      <div className={styles.links}>
        {navItems.map(({ path, label }) => (
          <NavLink
            key={label}
            to={path}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.active : ''}`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>

      <div className={styles.selectors}>
        <select
          className={styles.select}
          value={selectedSeason ?? ''}
          onChange={(e) => setSeason(e.target.value ? Number(e.target.value) : null)}
          aria-label="Select season"
        >
          <option value="" disabled>Season</option>
          {seasons?.map((s) => (
            <option key={s.season} value={s.season}>
              {s.season} Season
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={selectedSessionId ?? ''}
          onChange={(e) => setSessionId(e.target.value || null)}
          disabled={!races?.length}
          aria-label="Select race"
        >
          <option value="" disabled>
            {selectedSeason ? 'Select race' : '— select season first —'}
          </option>
          {races?.map((r) => (
            <option key={r.id} value={r.id}>
              Rd {String(r.round).padStart(2, '0')} — {r.circuit_name}
            </option>
          ))}
        </select>
      </div>
    </nav>
  )
}