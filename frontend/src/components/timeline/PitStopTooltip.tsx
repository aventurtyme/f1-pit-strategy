// ─────────────────────────────────────────────────────────
// components/timeline/PitStopTooltip.tsx
// Renders above the pit stop marker.
// Position is corrected via getBoundingClientRect to avoid
// viewport clipping (style guide §06).
// All PTL / PPD / UTS values show explicit +/− sign.
// font-variant-numeric: tabular-nums on all numerics.
// ─────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from 'react'
import type { PitStop } from '../../api/types'
import StrategyBadge from '../StrategyBadge'
import styles from './PitStopTooltip.module.css'

interface Props {
  pitStop: PitStop
  anchorEl: HTMLElement | SVGElement | null
  circuitName: string
}

function signed(n: number, decimals = 1): string {
  const abs = Math.abs(n).toFixed(decimals)
  return n >= 0 ? `+${abs}` : `−${abs}`
}

function ppdLabel(ppd: number): string {
  if (ppd === 0) return '0 pos'
  return `${ppd > 0 ? '+' : '−'}${Math.abs(ppd)} pos`
}

function utsColorVar(uts: number): string {
  if (uts > 0) return 'var(--uts-pos-text)'
  if (uts < 0) return 'var(--uts-neg-text)'
  return 'var(--uts-neu-text)'
}

export default function PitStopTooltip({ pitStop, anchorEl, circuitName }: Props) {
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })

  useEffect(() => {
    if (!anchorEl || !tooltipRef.current) return

    const anchor  = anchorEl.getBoundingClientRect()
    const tooltip = tooltipRef.current.getBoundingClientRect()
    const margin  = 8 // px gap between marker and tooltip

    // Default: centre-above the marker
    let top  = anchor.top - tooltip.height - margin + window.scrollY
    let left = anchor.left + anchor.width / 2 - tooltip.width / 2 + window.scrollX

    // Clamp left so tooltip stays within viewport
    const viewW = window.innerWidth
    if (left < 8) left = 8
    if (left + tooltip.width > viewW - 8) left = viewW - 8 - tooltip.width

    // If no room above, flip below
    if (top < 8) {
      top = anchor.bottom + margin + window.scrollY
    }

    setPos({ top, left })
  }, [anchorEl])

  const {
    driver_code, lap, gap_behind,
    tire_age_self, compound_self,
    tire_age_behind, compound_behind,
    ptl, ppd, uts, strategy_type,
    is_opportunistic, race_flag,
  } = pitStop

  return (
    <div
      ref={tooltipRef}
      className={styles.tooltip}
      style={{ top: pos.top, left: pos.left }}
      role="tooltip"
    >
      <div className={styles.header}>
        <div>
          <p className={styles.title}>{driver_code} · Lap {lap}</p>
          <StrategyBadge type={strategy_type} />
        </div>
        <span className="label-micro">{circuitName}</span>
      </div>

      <div className={styles.rows}>
        <div className={styles.row}>
          <span className={styles.key}>Gap behind</span>
          <span className={`${styles.val} tabular-nums`}>{gap_behind.toFixed(2)}s</span>
        </div>
        <div className={styles.row}>
          <span className={styles.key}>Tire age (self)</span>
          <span className={`${styles.val} tabular-nums`}>
            {tire_age_self} laps · {compound_self}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.key}>Tire age (behind)</span>
          <span className={`${styles.val} tabular-nums`}>
            {tire_age_behind} laps · {compound_behind}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.key}>PTL</span>
          <span className={`${styles.val} tabular-nums`}>{signed(ptl)}s</span>
        </div>
        <div className={styles.row}>
          <span className={styles.key}>PPD</span>
          <span className={`${styles.val} tabular-nums`}>{ppdLabel(ppd)}</span>
        </div>
        {is_opportunistic && (
          <div className={styles.row}>
            <span className={styles.key}>Flag</span>
            <span className={`${styles.val} tabular-nums`}>{race_flag.toUpperCase()}</span>
          </div>
        )}
      </div>

      <div className={styles.utsRow}>
        <span className={styles.key}>UTS</span>
        <span
          className={`${styles.utsScore} tabular-nums`}
          style={{ color: utsColorVar(uts) }}
        >
          {signed(uts)}
        </span>
      </div>
    </div>
  )
}