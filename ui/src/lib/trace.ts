import type { AllocationConfig, AllocationResult, Scenario, Trace } from '../api/models'

const SLACK_COMFORT_MIN = 120

export const cellKey = (ticketId: string, engineerId: string) => `${ticketId}|${engineerId}`

/** The two soft-cost terms for one cell, recomputed from the trace grids for the hover readout. */
export function costTerms(trace: Trace, config: AllocationConfig, i: number, j: number) {
  const roadKm = trace.road_km_grid[i][j]
  const slack = trace.slack_min_grid[i][j]
  const weights = config.weights ?? { distance: 1, slack: 0.5 }
  const maxKm = config.max_distance_km ?? 30
  const distance = (weights.distance ?? 1) * (roadKm / maxKm)
  const margin = (weights.slack ?? 0.5) * (1 - Math.min(Math.max(slack, 0) / SLACK_COMFORT_MIN, 1))
  return { roadKm, slack, distance, margin }
}

/** Plain words for one violation code on cell (i, j). */
export function violationText(
  code: string,
  scenario: Scenario,
  trace: Trace,
  config: AllocationConfig,
  i: number,
  j: number,
): string {
  const ticket = scenario.tickets.find((t) => t.id === trace.ticket_ids[i])
  switch (code) {
    case 'SKILL_MISMATCH':
      return `no ${ticket?.fault_type ?? 'matching'} skill`
    case 'TOO_FAR':
      return `${trace.road_km_grid[i][j].toFixed(1)} km away (limit ${config.max_distance_km ?? 30} km)`
    case 'OFF_SHIFT':
      return 'cannot finish inside shift'
    case 'MISSES_DEADLINE':
      return `late by ${-trace.slack_min_grid[i][j]} min`
    default:
      return code
  }
}

/** A ticket worth showing in the hard-filter step: urgent, with some engineers allowed and some not. */
export function defaultFocusTicket(trace: Trace, scenario: Scenario): string | undefined {
  const rank = { P1: 0, P2: 1, P3: 2 } as const
  const priority = new Map(scenario.tickets.map((t) => [t.id, rank[t.priority]]))
  const candidates = trace.ticket_ids.map((id, i) => {
    const allowed = trace.cost_grid[i].filter((c) => c !== null).length
    const mixed = allowed > 0 && allowed < trace.engineer_ids.length
    return { id, score: (mixed ? 0 : 10) + (priority.get(id) ?? 3) }
  })
  candidates.sort((a, b) => a.score - b.score)
  return candidates[0]?.id
}

export interface PickView {
  ticketId: string
  engineerId: string
  step: number
  cost: number | null
  /** The ticket the other algorithm gave this engineer to, when it differs. */
  grabbedFrom?: string
}

/** The left algorithm's picks in order, flagging engineers the right algorithm used elsewhere. */
export function picksWithConflicts(left: AllocationResult, right: AllocationResult | undefined): PickView[] {
  const trace = left.trace
  if (!trace) return []
  const rightTicketOf = new Map((right?.assignments ?? []).map((a) => [a.engineer_id, a.ticket_id]))
  return trace.pick_order.map((p) => {
    const i = trace.ticket_ids.indexOf(p.ticket_id)
    const j = trace.engineer_ids.indexOf(p.engineer_id)
    const other = rightTicketOf.get(p.engineer_id)
    return {
      ticketId: p.ticket_id,
      engineerId: p.engineer_id,
      step: p.step,
      cost: i >= 0 && j >= 0 ? trace.cost_grid[i][j] : null,
      grabbedFrom: other && other !== p.ticket_id ? other : undefined,
    }
  })
}

export function isSequential(result: AllocationResult): boolean {
  return new Set(result.trace?.pick_order.map((p) => p.step) ?? []).size > 1
}
