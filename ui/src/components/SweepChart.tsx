import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AlgorithmName, SweepPoint } from '../api/models'
import { ALGORITHM_COLOR } from '../lib/colors'
import { algorithmLabel } from '../lib/format'
import { pivot, type SweepMetric } from '../lib/sweep'

interface SweepChartProps {
  title: string
  points: SweepPoint[]
  metric: SweepMetric
  algorithms: AlgorithmName[]
  unit: string
  testId: string
}

/** One line per algorithm across the engineer-to-ticket ratio. */
export function SweepChart({ title, points, metric, algorithms, unit, testId }: SweepChartProps) {
  const rows = pivot(points, metric)
  return (
    <figure className="sweep-chart" data-testid={testId}>
      <figcaption>{title}</figcaption>
      <ResponsiveContainer width="100%" height={260} initialDimension={{ width: 480, height: 260 }}>
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 18, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
          <XAxis
            dataKey="ratio"
            type="number"
            domain={['dataMin', 'dataMax']}
            ticks={rows.map((r) => r.ratio)}
            fontSize={12}
            label={{ value: 'engineers per ticket', position: 'insideBottom', offset: -10, fontSize: 12 }}
          />
          <YAxis fontSize={12} width={52} unit={unit} />
          <Tooltip
            labelFormatter={(ratio) => `ratio ${String(ratio)}`}
            formatter={(value, name) => [
              value == null ? '—' : `${Number(value).toFixed(2)}${unit}`,
              algorithmLabel(String(name)),
            ]}
          />
          <Legend verticalAlign="top" height={28} formatter={(name) => algorithmLabel(String(name))} />
          {algorithms.map((name) => (
            <Line
              key={name}
              type="linear"
              dataKey={name}
              stroke={ALGORITHM_COLOR[name]}
              strokeWidth={2.5}
              dot={{ r: 3 }}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </figure>
  )
}
