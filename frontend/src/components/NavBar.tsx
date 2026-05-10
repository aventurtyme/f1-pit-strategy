// ─────────────────────────────────────────────────────────
// components/NavBar.tsx
// Fixed top nav: brand + route links + season/race selectors.
// Season and race selection is owned by Zustand + URL params;
// the NavBar renders what the store has and dispatches updates.
// ─────────────────────────────────────────────────────────

import { NavLink, useSearchParams } from 'react-router-dom'
import { useEffect } from 'react'
import { useSeasons, useRaces } from '../api/queries'
import useUiStore from '../store/uiStore'
import styles from './NavBar.module.css'

export default function NavBar() {
  const [searchParams, setSearchParams] = useSearchParams()

  const { selectedSeason, selectedSessionId, setSeason, setSessionId } = useUiStore()

  const { data: seasons } = useSeasons()
  const { data: races }   = useRaces(selectedSeason)

  // ── Hydrate store from URL on first mount ──────────────
  useEffect(() => {
    const urlSeason    = searchParams.get('season')
    const urlSessionId = searchParams.get('session')

    if (urlSeason && !selectedSeason) {
      setSeason(Number(urlSeason))
    }
    if (urlSessionId && !selectedSessionId) {
      setSessionId(urlSessionId)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Sync store → URL ───────────────────────────────────
  useEffect(() => {
    const next: Record<string, string> = {}
    if (selectedSeason)    next['season']  = String(selectedSeason)
    if (selectedSessionId) next['session'] = selectedSessionId
    setSearchParams(next, { replace: true })
  }, [selectedSeason, selectedSessionId, setSearchParams])

  function handleSeasonChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    setSeason(val ? Number(val) : null)
  }

  function handleRaceChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    setSessionId(val || null)
  }

  return (
    <nav className={styles.nav} aria-label="Main navigation">
      <span className={styles.brand}>Pit Analyzer</span>

      <div className={styles.links}>
        <NavLink
          to="/"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ''}`
          }
        >
          Timeline
        </NavLink>
        <NavLink
          to="/teams"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ''}`
          }
        >
          Teams
        </NavLink>
        <NavLink
          to="/circuits"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ''}`
          }
        >
          Circuits
        </NavLink>
        <NavLink
          to="/insights"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ''}`
          }
        >
          Insights
        </NavLink>
      </div>

      <div className={styles.selectors}>
        <select
          className={styles.select}
          value={selectedSeason ?? ''}
          onChange={handleSeasonChange}
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
          onChange={handleRaceChange}
          disabled={!races?.length}
          aria-label="Select race"
        >
          <option value="" disabled>
            {selectedSeason ? 'Select race' : '— select season first —'}
          </option>
          {races?.map((r) => (
            <option key={r.session_id} value={r.session_id}>
              Rd {String(r.round).padStart(2, '0')} — {r.circuit_name}
            </option>
          ))}
        </select>
      </div>
    </nav>
  )
}