import type { AlgorithmName, AllocationResult, Results } from '../api/models'
import { algorithmLabel, km, ms, num, pct } from '../lib/format'

interface Row {
  label: string
  value: (r: AllocationResult) => number | null
  format: (v: number | null) => string
  better: 'higher' | 'lower' | null
}

const ROWS: Row[] = [
  { label: 'Tickets served', value: (r) => r.metrics.assigned, format: (v) => num(v, 0), better: 'higher' },
  { label: 'Coverage', value: (r) => r.metrics.coverage_pct, format: (v) => pct(v), better: 'higher' },
  { label: 'P1 coverage', value: (r) => r.metrics.p1_coverage_pct, format: (v) => pct(v), better: 'higher' },
  {
    label: 'Priority-weighted coverage',
    value: (r) => r.metrics.priority_weighted_coverage,
    format: (v) => num(v, 2),
    better: 'higher',
  },
  { label: 'Total travel', value: (r) => r.metrics.total_km, format: (v) => km(v), better: 'lower' },
  { label: 'Average travel', value: (r) => r.metrics.avg_km, format: (v) => km(v), better: 'lower' },
  {
    label: 'Average deadline margin',
    value: (r) => r.metrics.avg_slack_min,
    format: (v) => (v == null ? '—' : `${v.toFixed(0)} min`),
    better: 'higher',
  },
  {
    label: 'Tight assignments (< 15 min)',
    value: (r) => r.metrics.tight_assignments,
    format: (v) => num(v, 0),
    better: 'lower',
  },
  { label: 'Engineer utilisation', value: (r) => r.metrics.utilization_pct, format: (v) => pct(v), better: null },
  { label: 'Objective', value: (r) => r.metrics.objective, format: (v) => num(v, 2), better: 'lower' },
  { label: 'Gap vs best', value: (r) => r.metrics.gap_vs_best_pct, format: (v) => pct(v), better: 'lower' },
  { label: 'Runtime', value: (r) => r.runtime_ms, format: (v) => (v == null ? '—' : ms(v)), better: 'lower' },
]

function bestOf(values: (number | null)[], better: Row['better']): number | null {
  const present = values.filter((v): v is number => v != null)
  if (!better || present.length < 2) return null
  const best = better === 'higher' ? Math.max(...present) : Math.min(...present)
  const worst = better === 'higher' ? Math.min(...present) : Math.max(...present)
  return Math.abs(best - worst) < 1e-9 ? null : best
}

interface MetricsTableProps {
  results: Results
  algorithms: AlgorithmName[]
}

/** Rows = metrics, columns = algorithms, best value in each row highlighted. */
export function MetricsTable({ results, algorithms }: MetricsTableProps) {
  const present = algorithms.filter((name) => results[name])
  return (
    <div className="table-wrap">
      <table className="metrics-table" data-testid="metrics-table">
        <thead>
          <tr>
            <th scope="col">Metric</th>
            {present.map((name) => (
              <th scope="col" key={name}>
                {algorithmLabel(name)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const values = present.map((name) => row.value(results[name] as AllocationResult))
            const best = bestOf(values, row.better)
            return (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                {values.map((value, i) => (
                  <td key={present[i]} className={best != null && value === best ? 'best' : undefined}>
                    {row.format(value)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
