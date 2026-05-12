import StrategyBadge from '../StrategyBadge';
import UtsScoreBlock from '../UtsScoreBlock';
import type { PitStopDetail } from '../../api/types';
import styles from './StopCard.module.css';

interface Props {
  stop: PitStopDetail;
  rank?: 'best' | 'worst';
}

export function StopCard({ stop, rank }: Props) {
  return (
    <div className={`${styles.card} ${rank ? styles[rank] : ''}`}>
      <div className={styles.header}>
        <div>
          <span className={styles.driver}>{stop.driver_code}</span>
          <span className={styles.meta}>Lap {stop.lap}</span>
        </div>
        <StrategyBadge type={stop.strategy_type} />
      </div>
      <div className={styles.stats}>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Gap behind</span>
          <span className={styles.statVal}>
            {stop.gap_behind != null ? `${stop.gap_behind.toFixed(1)}s` : '—'}
          </span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>PTL</span>
          <span className={styles.statVal}>
            {stop.ptl != null ? `${stop.ptl > 0 ? '+' : ''}${stop.ptl.toFixed(1)}` : '—'}
          </span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>PPD</span>
          <span className={styles.statVal}>
            {stop.ppd != null ? `${stop.ppd > 0 ? '+' : ''}${stop.ppd}` : '—'}
          </span>
        </div>
      </div>
      <UtsScoreBlock pitStop={stop} />
    </div>
  );
}