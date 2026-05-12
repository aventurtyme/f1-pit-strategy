interface Props {
  proactive: number;   // 0–1
  reactive: number;
  neutral: number;
}

export function StopRatioBar({ proactive, reactive, neutral }: Props) {
  const segments = [
    { label: 'Proactive', value: proactive, color: 'var(--uts-pos-bg-mid)', text: 'var(--uts-pos-text)' },
    { label: 'Neutral',   value: neutral,   color: 'var(--bg-border-strong)', text: 'var(--text-secondary)' },
    { label: 'Reactive',  value: reactive,  color: 'var(--uts-neg-bg-mid)', text: 'var(--uts-neg-text)' },
  ];

  return (
    <div>
      {/* Bar */}
      <div style={{ display: 'flex', height: '28px', borderRadius: '2px', overflow: 'hidden', gap: '2px' }}>
        {segments.map(s => (
          <div
            key={s.label}
            style={{
              width: `${s.value * 100}%`,
              background: s.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'width 0.3s ease-out',
            }}
          >
            {s.value > 0.12 && (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                color: s.text,
                letterSpacing: '0.04em',
              }}>
                {Math.round(s.value * 100)}%
              </span>
            )}
          </div>
        ))}
      </div>
      {/* Legend */}
      <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem' }}>
        {segments.map(s => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: s.color }} />
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--text-tertiary)',
            }}>
              {s.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}