import type { AlgorithmName, AllocationResult, Assignment, Metrics, Scenario } from '../api/models'

export function makeMetrics(overrides: Partial<Metrics> = {}): Metrics {
  return {
    assigned: 10,
    total_tickets: 12,
    coverage_pct: 83.3,
    p1_coverage_pct: 100,
    priority_weighted_coverage: 0.9,
    total_km: 80,
    avg_km: 8,
    avg_slack_min: 60,
    tight_assignments: 2,
    engineers_used: 10,
    utilization_pct: 90,
    objective: 20,
    gap_vs_best_pct: 0,
    unserved_by_priority: { P1: 0, P2: 1, P3: 1 },
    ...overrides,
  }
}

export function makeAssignment(ticketId: string, engineerId: string): Assignment {
  return {
    ticket_id: ticketId,
    engineer_id: engineerId,
    road_km: 5,
    travel_min: 10,
    duration_p50_min: 75,
    duration_p90_min: 75,
    start: '2026-10-20T09:10:00+05:30',
    finish: '2026-10-20T10:25:00+05:30',
    slack_min: 60,
    cost: 0.3,
    cost_breakdown: { distance: 0.2, slack: 0.1 },
    explanation: { summary: 'Nearest feasible electrical-skilled engineer', runner_ups: [] },
  }
}

export function makeResult(
  algorithm: AlgorithmName,
  metrics: Partial<Metrics> = {},
  pairs: [string, string][] = [['T01', 'E01']],
): AllocationResult {
  return {
    algorithm,
    runtime_ms: 0.5,
    assignments: pairs.map(([t, e]) => makeAssignment(t, e)),
    unassigned: [],
    metrics: makeMetrics(metrics),
    trace: null,
  }
}

export const SCENARIO: Scenario = {
  id: 'sc_1_2_2',
  seed: 1,
  dispatch_time: '2026-10-20T09:00:00+05:30',
  engineers: [
    {
      id: 'E01',
      name: 'Ravi',
      location: { lat: 12.97, lng: 77.59 },
      skills: ['electrical'],
      shift_start: '2026-10-20T08:00:00+05:30',
      shift_end: '2026-10-20T17:00:00+05:30',
      experience_years: 6,
    },
    {
      id: 'E02',
      name: 'Priya',
      location: { lat: 12.99, lng: 77.61 },
      skills: ['mechanical'],
      shift_start: '2026-10-20T08:00:00+05:30',
      shift_end: '2026-10-20T17:00:00+05:30',
      experience_years: 3,
    },
  ],
  tickets: [
    {
      id: 'T01',
      location: { lat: 12.98, lng: 77.6 },
      fault_type: 'electrical',
      priority: 'P1',
      deadline: '2026-10-20T13:00:00+05:30',
      equipment_age_years: 4,
      created_at: '2026-10-20T08:30:00+05:30',
    },
    {
      id: 'T02',
      location: { lat: 13.0, lng: 77.62 },
      fault_type: 'hydraulic',
      priority: 'P3',
      deadline: '2026-10-20T15:00:00+05:30',
      equipment_age_years: 9,
      created_at: '2026-10-20T08:10:00+05:30',
    },
  ],
}
