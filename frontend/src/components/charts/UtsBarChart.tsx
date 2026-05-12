import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';
import type { TeamRaceUts } from '../../api/types';

interface Props {
  data: TeamRaceUts[];
}

export function UtsBarChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
        <CartesianGrid
          strokeDasharray="0"
          stroke="var(--bg-border)"
          vertical={false}
        />
        <XAxis
          dataKey="circuit_name"
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-tertiary)' }}
          axisLine={false}
          tickLine={false}
          interval={2}
        />
        <YAxis
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-tertiary)' }}
          axisLine={false}
          tickLine={false}
          domain={[-100, 100]}
        />
        <ReferenceLine y={0} stroke="var(--bg-border-strong)" strokeWidth={1} />
        <Tooltip
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--bg-border-strong)',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
          }}
          formatter={(val: unknown) => [
            `${(val as number) > 0 ? '+' : ''}${(val as number).toFixed(1)}`,
            'Avg UTS',
          ]}
        />
        <Bar dataKey="avg_uts" radius={[2, 2, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={
                entry.avg_uts >= 20
                  ? 'var(--uts-pos-bg-mid)'
                  : entry.avg_uts <= -20
                  ? 'var(--uts-neg-bg-mid)'
                  : 'var(--bg-border-strong)'
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}