// ─────────────────────────────────────────────────────────
// views/TimelineView.tsx
// ─────────────────────────────────────────────────────────

import { useMemo } from 'react'
import useUiStore from '../store/uiStore'
import { useTimeline, usePitStops } from '../api/queries'
import RaceTimeline from '../components/timeline/RaceTimeline'
import StrategyBadge from '../components/StrategyBadge'
import SkeletonRow from '../components/SkeletonRow'
import type { DriverRow, MergedPitStop } from '../api/types'
import styles from './TimelineView.module.css'

function signed(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '—'
  const abs = Math.abs(n).toFixed(decimals)
  return n >= 0 ? `+${abs}` : `−${abs}`
}

function ppdLabel(ppd: number | null | undefined): string {
  if (ppd == null) return '—'
  if (ppd === 0) return '0'
  return `${ppd > 0 ? '+' : '−'}${Math.abs(ppd)}`
}

export default function TimelineView() {
  const { selectedSessionId } = useUiStore()

  const {
    data: timeline,
    isLoading: timelineLoading,
    isError: timelineError,
  } = useTimeline(selectedSessionId)

  const { data: pitStops } = usePitStops(selectedSessionId)

  const mergedEvents = useMemo((): MergedPitStop[] => {
    if (!timeline) return []
    const detailMap = new Map(pitStops?.map((s) => [s.id, s]) ?? [])
    return timeline.pit_events.map((ev): MergedPitStop => ({
      ...ev,
      ...(detailMap.get(ev.id) ?? {}),
    }))
  }, [timeline, pitStops])

  const driverRows = useMemo((): DriverRow[] => {
    const map = new Map<string, DriverRow>()
    for (const ev of mergedEvents) {
      if (!map.has(ev.driver_code)) {
        map.set(ev.driver_code, {
          driver_code: ev.driver_code,
          team: ev.team,
          pit_stops: [],
        })
      }
      map.get(ev.driver_code)!.pit_stops.push(ev)
    }
    return Array.from(map.values()).sort((a, b) =>
      a.driver_code.localeCompare(b.driver_code)
    )
  }, [mergedEvents])

  const tableRows = useMemo(
    () => [...mergedEvents].sort((a, b) => a.lap - b.lap),
    [mergedEvents]
  )

  if (!selectedSessionId) {
    return (
      <div className={styles.empty}>
        <p>Select a season and race from the dropdowns above.</p>
      </div>
    )
  }

  if (timelineLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.skeletonHeader}>
          <SkeletonRow rows={1} height={28} />
        </div>
        <div className={styles.timelineSkeleton}>
          <SkeletonRow rows={20} height={28} />
        </div>
      </div>
    )
  }

  if (timelineError || !timeline) {
    return (
      <div className={styles.empty}>
        <p>Failed to load timeline data. Check that the API is running.</p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <p className={styles.headerTag}>Race Timeline</p>
          <h1 className={styles.headerTitle}>{timeline.circuit_name}</h1>
        </div>
        <div className={styles.headerMeta}>
          <span className="label-micro">{timeline.season} · Round {timeline.round}</span>
          <span className="label-micro">{timeline.race_date}</span>
          <span className="label-micro">
            {driverRows.length} drivers · {mergedEvents.length} stops
          </span>
        </div>
      </div>

      <section className={styles.section}>
        <RaceTimeline
          drivers={driverRows}
          circuitName={timeline.circuit_name}
        />
      </section>

      <section className={styles.section}>
        <p className={styles.tableLabel}>Pit Stop Detail</p>

        {tableRows.length === 0 ? (
          <p className={styles.emptyInline}>No pit stop data available for this session.</p>
        ) : (
          <div className={styles.tableCard}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Driver</th>
                  <th>Team</th>
                  <th className={styles.r}>Lap</th>
                  <th className={styles.r}>Gap behind</th>
                  <th className={styles.r}>Tire age</th>
                  <th className={styles.r}>PTL</th>
                  <th className={styles.r}>PPD</th>
                  <th className={styles.r}>UTS</th>
                  <th>Strategy</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map((ps) => {
                  const tireAge = ps.tire_age_self ?? null

                  return (
                    <tr key={ps.id}>
                      <td className={styles.driver}>{ps.driver_code}</td>
                      <td>{ps.team}</td>
                      <td className={`${styles.r} tabular-nums`}>{ps.lap}</td>
                      <td className={`${styles.r} tabular-nums`}>
                        {ps.gap_behind != null ? `${ps.gap_behind.toFixed(2)}s` : '—'}
                      </td>
                      <td className={`${styles.r} tabular-nums`}>
                        {tireAge != null
                          ? `${tireAge}L · ${ps.compound_self ?? ''}`
                          : ps.compound_self ?? '—'}
                      </td>
                      <td className={`${styles.r} tabular-nums`}>{signed(ps.ptl)}s</td>
                      <td className={`${styles.r} tabular-nums`}>{ppdLabel(ps.ppd)}</td>
                      <td
                        className={`${styles.r} tabular-nums`}
                        style={{
                          color:
                            ps.uts == null
                              ? 'var(--text-tertiary)'
                              : ps.uts > 0
                              ? 'var(--uts-pos-text)'
                              : ps.uts < 0
                              ? 'var(--uts-neg-text)'
                              : 'var(--uts-neu-text)',
                        }}
                      >
                        {signed(ps.uts)}
                      </td>
                      <td>
                        <StrategyBadge type={ps.strategy_type} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}