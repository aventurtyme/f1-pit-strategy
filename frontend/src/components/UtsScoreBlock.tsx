// ─────────────────────────────────────────────────────────
// components/UtsScoreBlock.tsx
// UTS score display with semantic background + badge.
// PTL and PPD are always rendered with explicit +/− sign.
// font-variant-numeric: tabular-nums on all numbers.
// ─────────────────────────────────────────────────────────

import type { PitStop } from '../api/types'
import StrategyBadge from './StrategyBadge'
import styles from './UtsScoreBlock.module.css'

interface Props {
  pitStop: PitStop
}

function signedVal(n: number, decimals = 1): string {
  const fixed = Math.abs(n).toFixed(decimals)
  return n >= 0 ? `+${fixed}` : `−${fixed}`
}

function utsClass(uts: number): string {
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
          PPD: {ppd === 0 ? '0 pos' : `${ppd > 0 ? '+' : '−'}${Math.abs(ppd)} pos`}
        </span>
      </div>
    </div>
  )
}