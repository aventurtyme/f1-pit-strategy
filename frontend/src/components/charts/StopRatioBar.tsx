// ─────────────────────────────────────────────────────────
// components/charts/StopRatioBar.tsx
// Stacked ratio bar. Accepts raw counts (int) — the API
// returns proactive_stops / reactive_stops / neutral_stops
// as integers, not fractions. Fractions are derived here.
// ─────────────────────────────────────────────────────────

interface Props {
  proactive: number   // raw count
  reactive: number
  neutral: number
}

export function StopRatioBar({ proactive, reactive, neutral }: Props) {
  const total = proactive + reactive + neutral || 1   // guard against 0

  const segments = [
    {
      label: 'Proactive',
      count: proactive,
      frac: proactive / total,
      color: 'var(--uts-pos-bg-mid)',
      text: 'var(--uts-pos-text)',
    },
    {
      label: 'Neutral',
      count: neutral,
      frac: neutral / total,
      color: 'var(--bg-border-strong)',
      text: 'var(--text-secondary)',
    },
    {
      label: 'Reactive',
      count: reactive,
      frac: reactive / total,
      color: 'var(--uts-neg-bg-mid)',
      text: 'var(--uts-neg-text)',
    },
  ]

  return (
    <div>
      {/* Stacked bar */}
      <div
        style={{
          display: 'flex',
          height: '28px',
          borderRadius: '2px',
          overflow: 'hidden',
          gap: '2px',
        }}
      >
        {segments.map(s => (
          <div
            key={s.label}
            style={{
              width: `${s.frac * 100}%`,
              background: s.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'width 300ms ease-out',
            }}
          >
            {s.frac > 0.12 && (
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  color: s.text,
                  letterSpacing: '0.04em',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {Math.round(s.frac * 100)}%
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem' }}>
        {segments.map(s => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '2px',
                background: s.color,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
              }}
            >
              {s.label} ({s.count})
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}