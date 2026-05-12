import { useParams, useSearchParams } from 'react-router-dom';
import { useTeamProfile } from '../api/queries';
import { UtsBarChart } from '../components/charts/UtsBarChart';
import { StopRatioBar } from '../components/charts/StopRatioBar';
import { StopCard } from '../components/cards/StopCard';
import SkeletonRow from '../components/SkeletonRow';
import styles from './TeamView.module.css';

export function TeamView() {
  const { team } = useParams<{ team: string }>();
  const [searchParams] = useSearchParams();
  const season = parseInt(searchParams.get('season') ?? '2024', 10);

  const { data, isLoading, isError } = useTeamProfile(team ?? '', season);

  if (isLoading) return (
    <div className={styles.page}>
      {[1,2,3,4].map(i => <SkeletonRow key={i} />)}
    </div>
  );

  if (isError || !data) return (
    <div className={styles.page}>
      <p className={styles.empty}>No data available for this team.</p>
    </div>
  );

  const fmtUts = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`;

  return (
    <div className={styles.page}>

      {/* ── Page header ── */}
      <div className={styles.pageHeader}>
        <div>
          <p className={styles.tag}>Team Strategy Dashboard</p>
          <h1 className={styles.title}>{data.team}</h1>
        </div>
        <p className={styles.season}>{data.season} Season</p>
      </div>

      {/* ── Stat strip ── */}
      <div className={styles.statStrip}>
        {[
          { label: 'Avg UTS',       value: fmtUts(data.avg_uts),              sub: 'across all stops' },
          { label: 'Reactive rate', value: `${Math.round(data.reactive_stop_rate * 100)}%`, sub: 'of stops under threat' },
          { label: 'Pit lag index', value: `${data.pit_lag_index.toFixed(1)}`, sub: 'median laps late' },
          { label: 'Stops analysed',value: `${data.stops_analysed}`,          sub: `${data.season} season` },
        ].map(s => (
          <div key={s.label} className={styles.statCard}>
            <p className={styles.statLabel}>{s.label}</p>
            <p className={styles.statValue}
               style={{ color: s.label === 'Avg UTS'
                 ? data.avg_uts >= 0 ? 'var(--uts-pos-text)' : 'var(--uts-neg-text)'
                 : 'var(--text-primary)' }}>
              {s.value}
            </p>
            <p className={styles.statSub}>{s.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Charts row ── */}
      <div className={styles.chartsRow}>
        <div className={styles.chartCard}>
          <p className={styles.chartLabel}>Average UTS per race</p>
          <UtsBarChart data={data.race_uts} />
        </div>
        <div className={styles.chartCard}>
          <p className={styles.chartLabel}>Stop strategy breakdown</p>
          <div style={{ marginTop: '1.5rem' }}>
            <StopRatioBar
              proactive={data.proactive_stop_rate}
              reactive={data.reactive_stop_rate}
              neutral={data.neutral_stop_rate}
            />
          </div>
        </div>
      </div>

      {/* ── Best / worst stops ── */}
      <div className={styles.stopsRow}>
        <div>
          <p className={styles.chartLabel}>Best stops</p>
          <div className={styles.stopsList}>
            {data.best_stops.map(s => (
              <StopCard key={s.id} stop={s} rank="best" />
            ))}
          </div>
        </div>
        <div>
          <p className={styles.chartLabel}>Worst stops</p>
          <div className={styles.stopsList}>
            {data.worst_stops.map(s => (
              <StopCard key={s.id} stop={s} rank="worst" />
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}