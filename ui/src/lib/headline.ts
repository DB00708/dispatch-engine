import type { AllocationResult } from '../api/models'
import { algorithmLabel, plural } from './format'

export interface Headline {
  /** e.g. "Hungarian vs Greedy" — the better algorithm first. */
  title: string
  /** e.g. "+2 P1 tickets served, 14.3 km saved, 3 fewer tight deadlines" */
  detail: string
  /** True when there is no difference to report. */
  same: boolean
}

function sameDecisions(a: AllocationResult, b: AllocationResult): boolean {
  if (a.assignments.length !== b.assignments.length) return false
  const pairs = new Set(a.assignments.map((x) => `${x.ticket_id}:${x.engineer_id}`))
  return b.assignments.every((x) => pairs.has(`${x.ticket_id}:${x.engineer_id}`))
}

function change(count: number, noun: string, nouns: string, suffix: string): string {
  return `${count > 0 ? '+' : '−'}${plural(Math.abs(count), noun, nouns)} ${suffix}`
}

/**
 * The plain-words difference between two results on the same scenario, better one first.
 * "Better" means the lower objective: pairing costs plus penalties for unserved tickets.
 */
export function buildHeadline(first: AllocationResult, second: AllocationResult): Headline {
  if (first.algorithm === second.algorithm) {
    return {
      title: algorithmLabel(first.algorithm),
      detail: 'pick two different algorithms to compare them.',
      same: true,
    }
  }
  const [better, worse] =
    second.metrics.objective < first.metrics.objective - 1e-9 ? [second, first] : [first, second]
  const title = `${algorithmLabel(better.algorithm)} vs ${algorithmLabel(worse.algorithm)}`

  if (sameDecisions(better, worse)) {
    return {
      title,
      detail: `same ${plural(better.assignments.length, 'assignment')} on this scenario. Try fewer engineers to find where they part ways.`,
      same: true,
    }
  }

  const b = better.metrics
  const w = worse.metrics
  const parts: string[] = []

  const p1Gain = w.unserved_by_priority.P1 - b.unserved_by_priority.P1
  if (p1Gain !== 0) parts.push(change(p1Gain, 'P1 ticket', 'P1 tickets', 'served'))

  const servedGain = b.assigned - w.assigned
  if (servedGain !== 0 && servedGain !== p1Gain) {
    parts.push(change(servedGain, 'ticket', 'tickets', 'served in total'))
  }

  const kmSaved = w.total_km - b.total_km
  if (kmSaved >= 0.05) parts.push(`${kmSaved.toFixed(1)} km saved`)
  else if (kmSaved <= -0.05) parts.push(`${Math.abs(kmSaved).toFixed(1)} km more travel`)

  const tightFewer = w.tight_assignments - b.tight_assignments
  if (tightFewer !== 0) {
    parts.push(
      `${Math.abs(tightFewer)} ${tightFewer > 0 ? 'fewer' : 'more'} tight ${Math.abs(tightFewer) === 1 ? 'deadline' : 'deadlines'}`,
    )
  }

  if (w.objective > 0) {
    const drop = ((w.objective - b.objective) / w.objective) * 100
    if (drop >= 0.05) parts.push(`objective ${drop.toFixed(drop < 10 ? 1 : 0)}% lower`)
  }

  return { title, detail: parts.join(', ') || 'different choices, same overall cost', same: parts.length === 0 }
}
