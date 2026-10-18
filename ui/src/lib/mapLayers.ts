import type { AllocationResult, Scenario } from '../api/models'
import { clock } from './format'

export type EngineerState = 'used' | 'unused' | 'neutral' | 'feasible' | 'blocked'
export type LineKind = 'assigned' | 'tight' | 'ghost' | 'candidate'

export interface MapLine {
  ticketId: string
  engineerId: string
  kind: LineKind
  tooltip?: string
}

export interface MapLayers {
  lines: MapLine[]
  engineerState: Record<string, EngineerState>
  unassigned: Set<string>
}

/** Lines, engineer colours and unassigned tickets for one result on the map. */
export function resultLayers(
  scenario: Scenario,
  result: AllocationResult | undefined,
  tightSlackMin = 15,
): MapLayers {
  const engineerIds = new Set(scenario.engineers.map((e) => e.id))
  const ticketIds = new Set(scenario.tickets.map((t) => t.id))
  if (!result) {
    return {
      lines: [],
      engineerState: Object.fromEntries(scenario.engineers.map((e) => [e.id, 'neutral' as const])),
      unassigned: new Set(),
    }
  }
  // While a new result loads, the old one may mention removed ids: skip those.
  const assignments = result.assignments.filter(
    (a) => engineerIds.has(a.engineer_id) && ticketIds.has(a.ticket_id),
  )
  const used = new Set(assignments.map((a) => a.engineer_id))
  return {
    lines: assignments.map((a) => ({
      ticketId: a.ticket_id,
      engineerId: a.engineer_id,
      kind: a.slack_min < tightSlackMin ? 'tight' : 'assigned',
      tooltip: `${a.ticket_id} ← ${a.engineer_id} · ${a.road_km.toFixed(1)} km · ETA ${clock(a.start)} · finish ${clock(a.finish)} · ${a.slack_min} min spare`,
    })),
    engineerState: Object.fromEntries(
      scenario.engineers.map((e) => [e.id, used.has(e.id) ? 'used' : 'unused']),
    ),
    unassigned: new Set(result.unassigned.map((u) => u.ticket_id).filter((id) => ticketIds.has(id))),
  }
}
