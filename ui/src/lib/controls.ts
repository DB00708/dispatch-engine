import type { AlgorithmName, AllocationConfig, GenerateRequest } from '../api/models'

export const ALGORITHMS: AlgorithmName[] = ['greedy', 'hungarian', 'regret']

export interface Controls {
  seed: number
  numEngineers: number
  numTickets: number
  weights: { distance: number; slack: number }
  maxDistanceKm: number
  speedKmph: number
  estimator: 'naive' | 'ml'
  left: AlgorithmName
  right: AlgorithmName
}

export const DEFAULT_CONTROLS: Controls = {
  seed: 42,
  numEngineers: 12,
  numTickets: 20,
  weights: { distance: 1.0, slack: 0.5 },
  maxDistanceKm: 30,
  speedKmph: 30,
  estimator: 'naive',
  left: 'greedy',
  right: 'hungarian',
}

export function toGenerateRequest(c: Controls): GenerateRequest {
  return { seed: c.seed, num_engineers: c.numEngineers, num_tickets: c.numTickets }
}

export function toConfig(c: Controls): AllocationConfig {
  return {
    weights: c.weights,
    max_distance_km: c.maxDistanceKm,
    speed_kmph: c.speedKmph,
    estimator: c.estimator,
  }
}

export type EditMode = 'none' | 'add-engineer' | 'delete-ticket'
export type Tab = 'compare' | 'how' | 'experiment'
