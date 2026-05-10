// ─────────────────────────────────────────────────────────
// components/SkeletonRow.tsx
// Opacity-pulse skeleton per style guide §06.
// Renders at component level only — never full-page block.
// ─────────────────────────────────────────────────────────

import styles from './SkeletonRow.module.css'

interface Props {
  rows?: number
  height?: number
}

export default function SkeletonRow({ rows = 5, height = 20 }: Props) {
  return (
    <div className={styles.wrapper}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={styles.row}
          style={{ height }}
          // Stagger the animation slightly for a more natural feel
          aria-hidden="true"
        />
      ))}
    </div>
  )
}