// ─────────────────────────────────────────────────────────
// components/UtsScoreBlock.tsx
// UTS score display with semantic background + badge.
// Uses PitStopDetail (the full /pit-stops response shape).
// PTL and PPD rendered with explicit +/− sign.
// ─────────────────────────────────────────────────────────

import type { PitStopDetail } from '../api/types'
import StrategyBadge from './StrategyBadge'
import styles from './UtsScoreBlock.module.css'

interface Props {
  pitStop: PitStopDetail
}

function signedVal(n: number | null, decimals = 1): string {
  if (n == null) return '—'
  const fixed = Math.abs(n).toFixed(decimals)
  return n >= 0 ? `+${fixed}` : `−${fixed}`
}

function utsClass(uts: number | null): string {
  if (uts == null) return styles.neu
  if (uts > 0) return styles.pos
  if (uts < 0) return styles.neg
  return styles.neu
}

export default function UtsScoreBlock({ pitStop }: Props) {
  const { uts, ptl, ppd, strategy_type } = pitStop

  return (
    <div className={`${styles.block} ${utsClass(uts)}`}>
      <div>
        <p className={styles.label}>UTS Score</p>
        <div className={styles.scoreRow}>
          <span className={`${styles.score} tabular-nums`}>
            {signedVal(uts)}
          </span>
          <StrategyBadge type={strategy_type} />
        </div>
      </div>
      <div className={styles.meta}>
        <span className="tabular-nums">PTL: {signedVal(ptl)}s</span>
        <br />
        <span className="tabular-nums">
          PPD:{' '}
          {ppd == null
            ? '—'
            : ppd === 0
            ? '0 pos'
            : `${ppd > 0 ? '+' : '−'}${Math.abs(ppd)} pos`}
        </span>
      </div>
    </div>
  )
}