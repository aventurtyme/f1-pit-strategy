// ─────────────────────────────────────────────────────────
// components/StrategyBadge.tsx
// Proactive / Reactive / Neutral badge.
// Appears on pit stop markers, tooltip headers, and table rows.
// Never used as a general-purpose status badge.
// ─────────────────────────────────────────────────────────

import type { StrategyType } from '../api/types'
import styles from './StrategyBadge.module.css'

interface Props {
  type: StrategyType
}

const LABELS: Record<StrategyType, string> = {
  proactive: 'Proactive',
  reactive:  'Reactive',
  neutral:   'Neutral',
}

export default function StrategyBadge({ type }: Props) {
  return (
    <span className={`${styles.badge} ${styles[type]}`}>
      {LABELS[type]}
    </span>
  )
}