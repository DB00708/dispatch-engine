import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AlgorithmName, Results } from '../api/models'
import { ALGORITHM_COLOR } from '../lib/colors'
import { algorithmLabel } from '../lib/format'

interface ChartSpec {
  title: string
  unit: string
  value: (results: Results, name: AlgorithmName) => number
}

const CHARTS: ChartSpec[] = [
  { title: 'Coverage', unit: '%', value: (r, n) => r[n]?.metrics.coverage_pct ?? 0 },
  { title: 'Total travel', unit: 'km', value: (r, n) => r[n]?.metrics.total_km ?? 0 },
  { title: 'Objective (lower is better)', unit: '', value: (r, n) => r[n]?.metrics.objective ?? 0 },
]

interface MetricsChartProps {
  results: Results
  algorithms: AlgorithmName[]
}

/** Coverage, travel and objective per algorithm, as bars. */
export function MetricsChart({ results, algorithms }: MetricsChartProps) {
  const present = algorithms.filter((name) => results[name])
  return (
    <div className="mini-charts" data-testid="metrics-chart">
      {CHARTS.map((chart) => {
        const data = present.map((name) => ({
          name: algorithmLabel(name),
          algorithm: name,
          value: Number(chart.value(results, name).toFixed(2)),
        }))
        return (
          <figure key={chart.title} className="mini-chart">
            <figcaption>
              {chart.title}
              {chart.unit && <span className="muted"> ({chart.unit})</span>}
            </figcaption>
            <ResponsiveContainer width="100%" height={150} initialDimension={{ width: 240, height: 150 }}>
              <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={11} width={44} />
                <Tooltip cursor={{ fill: 'var(--hover)' }} formatter={(value) => [`${String(value)} ${chart.unit}`, chart.title]} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {data.map((d) => (
                    <Cell key={d.algorithm} fill={ALGORITHM_COLOR[d.algorithm]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </figure>
        )
      })}
    </div>
  )
}
