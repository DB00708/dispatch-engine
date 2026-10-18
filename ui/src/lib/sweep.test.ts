import { describe, expect, it } from 'vitest'
import type { SweepPoint } from '../api/models'
import { parseRatios, pivot, summarize } from './sweep'

const point = (ratio: number, algorithm: SweepPoint['algorithm'], gap: number, coverage: number): SweepPoint => ({
  ratio,
  num_engineers: Math.round(ratio * 30),
  algorithm,
  scenarios: 20,
  mean_objective: 100 + gap,
  mean_gap_pct: gap,
  p90_gap_pct: gap * 2,
  mean_coverage_pct: coverage,
  mean_p1_coverage_pct: 95,
  mean_runtime_ms: algorithm === 'regret' ? 1.4 : 0.2,
})

const POINTS = [
  point(0.5, 'greedy', 20, 48),
  point(0.5, 'hungarian', 0, 50),
  point(1, 'greedy', 160, 90),
  point(1, 'hungarian', 0, 97),
]

describe('sweep helpers', () => {
  it('parses, de-duplicates and sorts ratios', () => {
    expect(parseRatios('1, 0.5 0.75,0.5')).toEqual([0.5, 0.75, 1])
    expect(parseRatios('0.5, -1')).toBeNull()
    expect(parseRatios('abc')).toBeNull()
    expect(parseRatios('  ')).toBeNull()
  })

  it('pivots points into one row per ratio', () => {
    expect(pivot(POINTS, 'mean_gap_pct')).toEqual([
      { ratio: 0.5, engineers: 15, greedy: 20, hungarian: 0 },
      { ratio: 1, engineers: 30, greedy: 160, hungarian: 0 },
    ])
  })

  it('summarises where the heuristics fall furthest behind', () => {
    const lines = summarize(POINTS)
    expect(lines[0]).toBe(
      'Greedy is furthest from the best at ratio 1 (30 engineers): +160.0% on average, +320.0% in the worst 10% of scenarios; closest at ratio 0.5 (+20.0%).',
    )
    expect(lines[1]).toBe('Hungarian serves the most tickets at 2 of 2 ratios, because it optimises all tickets at once.')
    expect(lines[2]).toMatch(/^Every allocator averages under 1 ms/)
  })
})
