// ─────────────────────────────────────────────────────────
// views/CircuitsView.tsx
// Circuit list on the left, detail panel on the right.
// Season selector at top. Matches layout_proposal.html
// "Circuits" panel structure exactly.
// Populates circuit list from the races endpoint (distinct
// circuit_key + circuit_name from the selected season's races).
// ─────────────────────────────────────────────────────────

import { useState, useMemo } from 'react'
import { useSeasons, useRaces, useCircuitAnalysis } from '../api/queries'
import SkeletonRow from '../components/SkeletonRow'
import styles from './CircuitsView.module.css'

// ── Helpers ───────────────────────────────────────────────

function signed(v: number | null, decimals = 1): string {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)}`
}

function fmt(v: number | null, decimals = 1, suffix = ''): string {
  if (v == null) return '—'
  return `${v.toFixed(decimals)}${suffix}`
}

// ── Circuit list entry ────────────────────────────────────

interface CircuitEntry {
  circuit_key: string
  circuit_name: string
}

// ── Component ────────────────────────────────────────────

export function CircuitsView() {
  const { data: seasons } = useSeasons()
  const availableSeasons = seasons?.map(s => s.season).sort((a, b) => b - a) ?? []

  const [selectedSeason, setSelectedSeason] = useState<number | undefined>(undefined)
  const [selectedCircuit, setSelectedCircuit] = useState<string | null>(null)

  // We use the most recent season's races to build the circuit list.
  // If "All" is selected, fall back to the most recent available season for the list.
  const listSeason = selectedSeason ?? availableSeasons[0] ?? null
  const { data: races, isLoading: racesLoading } = useRaces(listSeason)

  // Deduplicate circuits from the race list, preserving round order
  const circuits = useMemo<CircuitEntry[]>(() => {
    if (!races) return []
    const seen = new Set<string>()
    return races
      .filter(r => {
        if (seen.has(r.circuit_key)) return false
        seen.add(r.circuit_key)
        return true
      })
      .map(r => ({ circuit_key: r.circuit_key, circuit_name: r.circuit_name }))
  }, [races])

  const activeKey = selectedCircuit && circuits.some(c => c.circuit_key === selectedCircuit)
    ? selectedCircuit
    : circuits[0]?.circuit_key ?? null

  const { data: analysis, isLoading: analysisLoading, isError } =
    useCircuitAnalysis(activeKey ?? '', selectedSeason)

  const isLoading = racesLoading || analysisLoading

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

      {/* ── Two-column layout ── */}
      <div className={styles.columns}>

        {/* Circuit list */}
        <div className={styles.circuitList}>
          {racesLoading && (
            <div className={styles.listSkeleton}>
              {[1, 2, 3, 4, 5].map(i => <div key={i} className={styles.skeletonItem} />)}
            </div>
          )}
          {circuits.map(c => (
            <button
              key={c.circuit_key}
              className={`${styles.circuitItem} ${activeKey === c.circuit_key ? styles.circuitActive : ''}`}
              onClick={() => setSelectedCircuit(c.circuit_key)}
            >
              <p className={styles.circuitName}>{c.circuit_name}</p>
              <p className={styles.circuitKey}>{c.circuit_key}</p>
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div className={styles.detail}>
          {isLoading && (
            <div className={styles.detailSkeleton}>
              {[1, 2, 3].map(i => <SkeletonRow key={i} />)}
            </div>
          )}

          {!isLoading && (isError || !analysis) && (
            <p className={styles.empty}>No data available for this circuit.</p>
          )}

          {!isLoading && analysis && (
            <>
              {/* Header */}
              <div className={styles.detailHeader}>
                <div>
                  <p className={styles.detailTag}>Circuit Analysis</p>
                  <h1 className={styles.detailTitle}>
                    {analysis.circuit_name ?? activeKey}
                  </h1>
                </div>
                {analysis.circuit_type && (
                  <span className={styles.typeBadge}>{analysis.circuit_type}</span>
                )}
              </div>

              {/* Stat strip */}
              <div className={styles.statRow}>
                {[
                  {
                    label: 'Avg UTS',
                    value: signed(analysis.avg_uts),
                    sub: 'all scored stops',
                    colored: true,
                    colorVal: analysis.avg_uts,
                  },
                  {
                    label: 'Below median',
                    value: fmt(analysis.negative_uts_pct, 1, '%'),
                    sub: 'of scored stops',
                    colored: false,
                    colorVal: null,
                  },
                  {
                    label: 'Avg gap at pit',
                    value: fmt(analysis.avg_gap_behind_at_pit, 1, 's'),
                    sub: 'green stops only',
                    colored: false,
                    colorVal: null,
                  },
                  {
                    label: 'Pit loss est.',
                    value: fmt(analysis.pit_loss_estimate, 0, 's'),
                    sub: 'circuit constant',
                    colored: false,
                    colorVal: null,
                  },
                ].map(s => (
                  <div key={s.label} className={styles.statCard}>
                    <p className={styles.statLabel}>{s.label}</p>
                    <p
                      className={styles.statValue}
                      style={
                        s.colored && s.colorVal != null
                          ? {
                              color:
                                s.colorVal >= 0
                                  ? 'var(--uts-pos-text)'
                                  : 'var(--uts-neg-text)',
                            }
                          : {}
                      }
                    >
                      {s.value}
                    </p>
                    <p className={styles.statSub}>{s.sub}</p>
                  </div>
                ))}
              </div>

              {/* Second stat row */}
              <div className={styles.statRowSmall}>
                {[
                  {
                    label: 'Green stops',
                    value: `${analysis.total_green_stops}`,
                    sub: 'SC excluded',
                  },
                  {
                    label: 'SC stops',
                    value: `${analysis.total_sc_stops}`,
                    sub: 'safety car / VSC',
                  },
                  {
                    label: 'Avg PPD',
                    value: fmt(analysis.avg_ppd, 1),
                    sub: 'pos delta after pit',
                  },
                  {
                    label: 'SC loss factor',
                    value: fmt(analysis.sc_loss_factor, 2, '×'),
                    sub: 'applied to pit loss',
                  },
                ].map(s => (
                  <div key={s.label} className={`${styles.statCard} ${styles.statCardSm}`}>
                    <p className={styles.statLabel}>{s.label}</p>
                    <p className={`${styles.statValue} ${styles.statValueSm}`}>{s.value}</p>
                    <p className={styles.statSub}>{s.sub}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}