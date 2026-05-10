// ─────────────────────────────────────────────────────────
// views/NotFound.tsx
// Plain 404 — no illustrations, no CTAs per style guide §06.
// ─────────────────────────────────────────────────────────

import styles from './NotFound.module.css'

export default function NotFound() {
  return (
    <div className={styles.wrapper}>
      <p className={styles.code}>404</p>
      <p className={styles.msg}>Page not found.</p>
    </div>
  )
}