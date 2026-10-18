import { describe, expect, it } from 'vitest'
import { makeResult } from '../test/fixtures'
import { buildHeadline } from './headline'

describe('buildHeadline', () => {
  it('puts the lower-objective algorithm first and lists every difference', () => {
    const greedy = makeResult(
      'greedy',
      { objective: 120, assigned: 9, total_km: 100, tight_assignments: 4, unserved_by_priority: { P1: 2, P2: 1, P3: 0 } },
      [['T01', 'E01']],
    )
    const hungarian = makeResult(
      'hungarian',
      { objective: 30, assigned: 11, total_km: 85.7, tight_assignments: 1, unserved_by_priority: { P1: 0, P2: 1, P3: 0 } },
      [['T01', 'E02']],
    )
    const headline = buildHeadline(greedy, hungarian)
    expect(headline.title).toBe('Hungarian vs Greedy')
    expect(headline.detail).toBe('+2 P1 tickets served, 14.3 km saved, 3 fewer tight deadlines, objective 75% lower')
    expect(headline.same).toBe(false)
  })

  it('mentions extra tickets when they are not all P1, and extra travel', () => {
    const regret = makeResult('regret', { objective: 50, assigned: 8, total_km: 60, tight_assignments: 2 }, [['T01', 'E01']])
    const hungarian = makeResult('hungarian', { objective: 45, assigned: 10, total_km: 70, tight_assignments: 1 }, [
      ['T01', 'E02'],
    ])
    expect(buildHeadline(hungarian, regret).detail).toBe(
      '+2 tickets served in total, 10.0 km more travel, 1 fewer tight deadline, objective 10% lower',
    )
  })

  it('says so when both algorithms made the same decisions', () => {
    const a = makeResult('greedy', { objective: 12 }, [['T01', 'E01']])
    const b = makeResult('hungarian', { objective: 12 }, [['T01', 'E01']])
    const headline = buildHeadline(a, b)
    expect(headline.same).toBe(true)
    expect(headline.detail).toMatch(/^same 1 assignment on this scenario/)
  })

  it('asks for two different algorithms when both sides match', () => {
    const a = makeResult('greedy')
    expect(buildHeadline(a, a).detail).toMatch(/pick two different algorithms/)
  })
})
