// ─────────────────────────────────────────────────────────
// components/timeline/PitStopTooltip.tsx
// Works with MergedPitStop — gracefully handles fields that
// may be absent if /pit-stops hasn't resolved yet.
// ─────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from 'react'
import type { MergedPitStop } from '../../api/types'
import StrategyBadge from '../StrategyBadge'
import styles from './PitStopTooltip.module.css'

interface Props {
  pitStop: MergedPitStop
  anchorEl: HTMLElement | SVGElement | null
  circuitName: string
}

function signed(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '—'
  const abs = Math.abs(n).toFixed(decimals)
  return n >= 0 ? `+${abs}` : `−${abs}`
}

function ppdLabel(ppd: number | null | undefined): string {
  if (ppd == null) return '—'
  if (ppd === 0) return '0 pos'
  return `${ppd > 0 ? '+' : '−'}${Math.abs(ppd)} pos`
}

function utsColor(uts: number | null): string {
  if (uts == null) return 'var(--text-tertiary)'
  if (uts > 0)     return 'var(--uts-pos-text)'
  if (uts < 0)     return 'var(--uts-neg-text)'
  return 'var(--uts-neu-text)'
}

export default function PitStopTooltip({ pitStop, anchorEl, circuitName }: Props) {
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState({ top: 0, left: 0 })

  useEffect(() => {
    if (!anchorEl || !tooltipRef.current) return
    const anchor  = anchorEl.getBoundingClientRect()
    const tooltip = tooltipRef.current.getBoundingClientRect()
    const margin  = 8

    let top  = anchor.top - tooltip.height - margin + window.scrollY
    let left = anchor.left + anchor.width / 2 - tooltip.width / 2 + window.scrollX

    const viewW = window.innerWidth
    if (left < 8) left = 8
    if (left + tooltip.width > viewW - 8) left = viewW - 8 - tooltip.width
    if (top < 8) top = anchor.bottom + margin + window.scrollY

    setPos({ top, left })
  }, [anchorEl])

  const {
    driver_code, lap, gap_behind,
    compound_self, race_flag,
    ptl, ppd, uts, strategy_type,
    is_opportunistic,
  } = pitStop

  // Fields only present after /pit-stops merges in
  const tire_age_self    = 'tire_age_self'    in pitStop ? (pitStop as { tire_age_self?: number }).tire_age_self    : null
  const tire_age_behind  = 'tire_age_behind'  in pitStop ? (pitStop as { tire_age_behind?: number }).tire_age_behind  : null
  const compound_behind  = 'compound_behind'  in pitStop ? (pitStop as { compound_behind?: string }).compound_behind  : null

  const isSc = race_flag === 'sc' || race_flag === 'vsc' || race_flag === 'red'

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

      {isSc && (
        <p className={styles.scNote}>
          {race_flag.toUpperCase()} stop — UTS not scored
        </p>
      )}

      <div className={styles.rows}>
        <div className={styles.row}>
          <span className={styles.key}>Gap behind</span>
          <span className={`${styles.val} tabular-nums`}>
            {gap_behind != null ? `${gap_behind.toFixed(2)}s` : '—'}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.key}>Tire age (self)</span>
          <span className={`${styles.val} tabular-nums`}>
            {tire_age_self != null ? `${tire_age_self} laps` : '—'}
            {compound_self ? ` · ${compound_self}` : ''}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.key}>Tire age (behind)</span>
          <span className={`${styles.val} tabular-nums`}>
            {tire_age_behind != null ? `${tire_age_behind} laps` : '—'}
            {compound_behind ? ` · ${compound_behind}` : ''}
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

      {!isSc && (
        <div className={styles.utsRow}>
          <span className={styles.key}>UTS</span>
          <span
            className={`${styles.utsScore} tabular-nums`}
            style={{ color: utsColor(uts) }}
          >
            {signed(uts)}
          </span>
        </div>
      )}
    </div>
  )
}