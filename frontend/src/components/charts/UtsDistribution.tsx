import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

interface Props {
  data: { bucket: string; count: number }[];
}

export function UtsDistribution({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
        <CartesianGrid stroke="var(--bg-border)" vertical={false} strokeDasharray="0" />
        <XAxis
          dataKey="bucket"
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-tertiary)' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-tertiary)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--bg-border-strong)',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
          }}
        />
        <Bar dataKey="count" radius={[2, 2, 0, 0]}>
          {data.map((entry, i) => {
            const mid = parseFloat(entry.bucket);
            return (
              <Cell
                key={i}
                fill={
                  mid > 20
                    ? 'var(--uts-pos-bg-mid)'
                    : mid < -20
                    ? 'var(--uts-neg-bg-mid)'
                    : 'var(--bg-border-strong)'
                }
              />
            );
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}