// ─────────────────────────────────────────────────────────
// views/InsightsView.tsx
// Replaces InsightsPanel stub. Wired to GET /insights/undercut-ranking.
// Season selector (All / per-year). Best + worst ranked stops.
// Matches the "Insights" panel in layout_proposal.html.
// ─────────────────────────────────────────────────────────

import { useState } from 'react'
import { useInsights, useSeasons } from '../api/queries'
import StrategyBadge from '../components/StrategyBadge'
import SkeletonRow from '../components/SkeletonRow'
import type { RankedStop } from '../api/types'
import styles from './InsightsView.module.css'

// ── Helper ────────────────────────────────────────────────

function signed(v: number | null, decimals = 1): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)}`
}

// ── Ranked stop row ───────────────────────────────────────

function RankedStopRow({ item, polarity }: { item: RankedStop; polarity: 'best' | 'worst' }) {
  const { stop, circuit_name, season, round } = item
  const isPos = (stop.uts ?? 0) >= 0
  return (
    <div className={styles.rankRow}>
      <span className={styles.rankNum}>#{item.rank}</span>
      <span className={styles.rankDriver}>{stop.driver_code}</span>
      <span className={styles.rankCircuit}>
        {circuit_name} · Rd {round} · {season} · Lap {stop.lap}
      </span>
      <StrategyBadge type={stop.strategy_type} />
      <span
        className={styles.rankUts}
        style={{ color: isPos ? 'var(--uts-pos-text)' : 'var(--uts-neg-text)' }}
      >
        {signed(stop.uts)}
      </span>
    </div>
  )
}

// ── Component ────────────────────────────────────────────

export function InsightsView() {
  const { data: seasons } = useSeasons()
  const availableSeasons = seasons?.map(s => s.season).sort((a, b) => b - a) ?? []

  const [selectedSeason, setSelectedSeason] = useState<number | undefined>(undefined)

  const { data, isLoading, isError } = useInsights(selectedSeason, 10)

  return (
    <div className={styles.page}>

      {/* ── Season selector ── */}
      <div className={styles.ctrl}>
        <span className={styles.ctrlLabel}>Season</span>
        <div className={styles.seasonSeg}>
          <button
            className={`${styles.segBtn} ${!selectedSeason ? styles.segActive : ''}`}
            onClick={() => setSelectedSeason(undefined)}
          >
            All
          </button>
          {availableSeasons.map(s => (
            <button
              key={s}
              className={`${styles.segBtn} ${selectedSeason === s ? styles.segActive : ''}`}
              onClick={() => setSelectedSeason(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* ── Body ── */}
      <div className={styles.body}>

        {isLoading && (
          <div className={styles.skeletons}>
            {[1, 2, 3, 4, 5].map(i => <SkeletonRow key={i} />)}
          </div>
        )}

        {!isLoading && (isError || !data) && (
          <p className={styles.empty}>No ranking data available.</p>
        )}

        {!isLoading && data && (
          <div className={styles.twoCol}>

            {/* Best stops */}
            <div>
              <p className={styles.sectionTitle}>Best UTS stops</p>
              <div className={styles.rankCard}>
                {data.best.map(item => (
                  <RankedStopRow key={item.stop.id} item={item} polarity="best" />
                ))}
                {data.best.length === 0 && (
                  <p className={styles.empty}>No stops found.</p>
                )}
              </div>
            </div>

            {/* Worst stops */}
            <div>
              <p className={styles.sectionTitle}>Worst UTS stops</p>
              <div className={styles.rankCard}>
                {data.worst.map(item => (
                  <RankedStopRow key={item.stop.id} item={item} polarity="worst" />
                ))}
                {data.worst.length === 0 && (
                  <p className={styles.empty}>No stops found.</p>
                )}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  )
}