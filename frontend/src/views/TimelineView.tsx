// ─────────────────────────────────────────────────────────
// views/TimelineView.tsx
// Primary view. Layout:
//   - Race header (circuit name + lap count + computed_at)
//   - D3 RaceTimeline
//   - Pit stops data table
//
// Loading: skeleton rows (no spinners).
// Empty: plain DM Mono text, centred, text-tertiary.
// ─────────────────────────────────────────────────────────

import useUiStore from '../store/uiStore'
import { useTimeline } from '../api/queries'
import RaceTimeline from '../components/timeline/RaceTimeline'
import StrategyBadge from '../components/StrategyBadge'
import SkeletonRow from '../components/SkeletonRow'
import styles from './TimelineView.module.css'

function signed(n: number, decimals = 1): string {
  const abs = Math.abs(n).toFixed(decimals)
  return n >= 0 ? `+${abs}` : `−${abs}`
}

function ppdLabel(ppd: number): string {
  if (ppd === 0) return '0'
  return `${ppd > 0 ? '+' : '−'}${Math.abs(ppd)}`
}

export default function TimelineView() {
  const { selectedSessionId } = useUiStore()
  const { data, isLoading, isError } = useTimeline(selectedSessionId)

  // ── Empty / prompt state ──────────────────────────────
  if (!selectedSessionId) {
    return (
      <div className={styles.empty}>
        <p>Select a season and race from the dropdowns above.</p>
      </div>
    )
  }

  // ── Loading state ─────────────────────────────────────
  if (isLoading) {
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

  // ── Error state ───────────────────────────────────────
  if (isError || !data) {
    return (
      <div className={styles.empty}>
        <p>Failed to load timeline data. Check that the API is running.</p>
      </div>
    )
  }

  // ── Flatten all pit stops for the table ───────────────
  const allPitStops = data.drivers.flatMap((d) =>
    d.pit_stops.map((ps) => ({ ...ps, driver_code: d.driver_code, team: d.team }))
  ).sort((a, b) => a.lap - b.lap)

  return (
    <div className={styles.container}>
      {/* ── Race header ── */}
      <div className={styles.header}>
        <div>
          <p className={styles.headerTag}>Race Timeline</p>
          <h1 className={styles.headerTitle}>{data.circuit_name}</h1>
        </div>
        <div className={styles.headerMeta}>
          <span className="label-micro">{data.season} · Round {data.round}</span>
          <span className="label-micro">{data.total_laps} laps</span>
          <span className="label-micro">{data.drivers.length} drivers</span>
        </div>
      </div>

      {/* ── D3 Timeline ── */}
      <section className={styles.section}>
        <RaceTimeline
          drivers={data.drivers}
          totalLaps={data.total_laps}
          circuitName={data.circuit_name}
        />
      </section>

      {/* ── Pit stops table ── */}
      <section className={styles.section}>
        <p className={styles.tableLabel}>Pit Stop Detail</p>

        {allPitStops.length === 0 ? (
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
                {allPitStops.map((ps) => (
                  <tr key={ps.id}>
                    <td className={styles.driver}>{ps.driver_code}</td>
                    <td>{ps.team}</td>
                    <td className={`${styles.r} tabular-nums`}>{ps.lap}</td>
                    <td className={`${styles.r} tabular-nums`}>{ps.gap_behind.toFixed(2)}s</td>
                    <td className={`${styles.r} tabular-nums`}>
                      {ps.tire_age_self}L · {ps.compound_self}
                    </td>
                    <td className={`${styles.r} tabular-nums`}>{signed(ps.ptl)}s</td>
                    <td className={`${styles.r} tabular-nums`}>{ppdLabel(ps.ppd)}</td>
                    <td
                      className={`${styles.r} tabular-nums`}
                      style={{
                        color:
                          ps.uts > 0
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}