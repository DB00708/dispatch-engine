import type { AlgorithmName } from '../api/models'

/** Chart colours per algorithm: grey = Greedy, blue = Hungarian (as in the design), rose = Regret. */
export const ALGORITHM_COLOR: Record<AlgorithmName, string> = {
  greedy: '#8b93a1',
  hungarian: '#4f6bed',
  regret: '#d0638a',
}

export const PRIORITY_COLOR = {
  P1: '#dc2626',
  P2: '#d97706',
  P3: '#2f80ed',
} as const
