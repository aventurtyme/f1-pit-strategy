import { useParams } from 'react-router-dom';
import { useCircuitAnalysis } from '../api/queries';
import { UtsDistribution } from '../components/charts/UtsDistribution';
import SkeletonRow from '../components/SkeletonRow';
import styles from './CircuitView.module.css';

export function CircuitView() {
  const { circuitKey } = useParams<{ circuitKey: string }>();
  const { data, isLoading, isError } = useCircuitAnalysis(circuitKey ?? '');

  if (isLoading) return (
    <div className={styles.page}>
      {[1,2,3].map(i => <SkeletonRow key={i} />)}
    </div>
  );

  if (isError || !data) return (
    <div className={styles.page}>
      <p className={styles.empty}>No data available for this circuit.</p>
    </div>
  );

  const corrLabel = (v: number) =>
    v > 0.5 ? 'Strong — late calls reliably cost positions here'
    : v > 0.2 ? 'Moderate — some correlation'
    : 'Weak — timing has limited impact';

  return (
    <div className={styles.page}>

      {/* ── Header ── */}
      <div className={styles.pageHeader}>
        <div>
          <p className={styles.tag}>Circuit Analysis</p>
          <h1 className={styles.title}>{data.circuit_name}</h1>
        </div>
        <span className={styles.typeBadge}>{data.circuit_type}</span>
      </div>

      {/* ── Stat strip ── */}
      <div className={styles.statStrip}>
        {[
          { label: 'Avg UTS',              value: `${data.avg_uts > 0 ? '+' : ''}${data.avg_uts.toFixed(1)}`,     colored: true },
          { label: 'Negative UTS rate',    value: `${Math.round(data.negative_uts_rate * 100)}%`,                  colored: false },
          { label: 'Avg gap at pit',       value: `${data.avg_gap_behind.toFixed(1)}s`,                           colored: false },
          { label: 'Pit loss estimate',    value: `${data.pit_loss_estimate}s`,                                   colored: false },
          { label: 'Punishment score',     value: data.circuit_punishment_score.toFixed(1),                       colored: false },
          { label: 'Stops analysed',       value: `${data.stops_analysed}`,                                       colored: false },
        ].map(s => (
          <div key={s.label} className={styles.statCard}>
            <p className={styles.statLabel}>{s.label}</p>
            <p className={styles.statValue}
               style={s.colored ? {
                 color: data.avg_uts >= 0 ? 'var(--uts-pos-text)' : 'var(--uts-neg-text)'
               } : {}}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {/* ── Charts row ── */}
      <div className={styles.chartsRow}>
        <div className={styles.chartCard}>
          <p className={styles.chartLabel}>UTS score distribution</p>
          <UtsDistribution data={data.uts_distribution} />
        </div>

        <div className={styles.chartCard}>
          <p className={styles.chartLabel}>Late call correlation</p>
          <div className={styles.corrBlock}>
            <p className={styles.corrValue}>
              {data.late_call_position_correlation.toFixed(2)}
            </p>
            <p className={styles.corrDesc}>
              {corrLabel(data.late_call_position_correlation)}
            </p>
            {/* Visual bar */}
            <div className={styles.corrBar}>
              <div
                className={styles.corrFill}
                style={{
                  width: `${Math.abs(data.late_call_position_correlation) * 100}%`,
                  background: data.late_call_position_correlation > 0.3
                    ? 'var(--uts-neg-bg-mid)'
                    : 'var(--bg-border-strong)',
                }}
              />
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}