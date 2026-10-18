import type { AlgorithmName, SweepPoint } from '../api/models'
import { algorithmLabel } from './format'

export type SweepMetric = 'mean_gap_pct' | 'p90_gap_pct' | 'mean_coverage_pct' | 'mean_p1_coverage_pct' | 'mean_runtime_ms'

export type SweepRow = { ratio: number; engineers: number } & Partial<Record<AlgorithmName, number | null>>

/** One row per ratio with a column per algorithm, the shape line charts want. */
export function pivot(points: SweepPoint[], metric: SweepMetric): SweepRow[] {
  const rows = new Map<number, SweepRow>()
  for (const point of points) {
    const row = rows.get(point.ratio) ?? { ratio: point.ratio, engineers: point.num_engineers }
    row[point.algorithm] = point[metric]
    rows.set(point.ratio, row)
  }
  return [...rows.values()].sort((a, b) => a.ratio - b.ratio)
}

/** "0.3, 0.5, 1" -> [0.3, 0.5, 1]; null when any entry is not a positive number. */
export function parseRatios(text: string): number[] | null {
  const parts = text
    .split(/[,\s]+/)
    .map((p) => p.trim())
    .filter(Boolean)
  if (parts.length === 0) return null
  const values = parts.map(Number)
  if (values.some((v) => !Number.isFinite(v) || v <= 0)) return null
  return [...new Set(values)].sort((a, b) => a - b)
}

/** Plain-words findings for the write-up, computed from the sweep itself. */
export function summarize(points: SweepPoint[]): string[] {
  if (points.length === 0) return []
  const findings: string[] = []
  const algorithms = [...new Set(points.map((p) => p.algorithm))]

  for (const name of algorithms.filter((a) => a !== 'hungarian')) {
    const own = points.filter((p) => p.algorithm === name && p.mean_gap_pct != null)
    if (own.length === 0) continue
    const worst = own.reduce((a, b) => ((b.mean_gap_pct ?? 0) > (a.mean_gap_pct ?? 0) ? b : a))
    const best = own.reduce((a, b) => ((b.mean_gap_pct ?? 0) < (a.mean_gap_pct ?? 0) ? b : a))
    findings.push(
      `${algorithmLabel(name)} is furthest from the best at ratio ${worst.ratio} (${worst.num_engineers} engineers): ` +
        `+${(worst.mean_gap_pct ?? 0).toFixed(1)}% on average, +${(worst.p90_gap_pct ?? 0).toFixed(1)}% in the worst 10% of scenarios; ` +
        `closest at ratio ${best.ratio} (+${(best.mean_gap_pct ?? 0).toFixed(1)}%).`,
    )
  }

  if (algorithms.includes('hungarian')) {
    const ratios = [...new Set(points.map((p) => p.ratio))]
    const leads = ratios.filter((ratio) => {
      const at = points.filter((p) => p.ratio === ratio)
      const hungarian = at.find((p) => p.algorithm === 'hungarian')?.mean_coverage_pct ?? 0
      return at.every((p) => (p.mean_coverage_pct ?? 0) <= hungarian + 1e-9)
    })
    findings.push(
      `Hungarian serves the most tickets at ${leads.length} of ${ratios.length} ratios, because it optimises all tickets at once.`,
    )
  }

  const slowest = points.reduce((a, b) => (b.mean_runtime_ms > a.mean_runtime_ms ? b : a))
  findings.push(
    `Every allocator averages under ${Math.max(1, Math.ceil(slowest.mean_runtime_ms))} ms per scenario; the slowest is ${algorithmLabel(slowest.algorithm)} at ratio ${slowest.ratio}.`,
  )
  return findings
}
