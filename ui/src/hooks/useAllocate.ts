import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { AlgorithmName, AllocationConfig, Scenario } from '../api/models'

interface AllocateArgs {
  scenario: Scenario | undefined
  config: AllocationConfig
  algorithms: AlgorithmName[]
  includeTrace?: boolean
  enabled?: boolean
}

/**
 * Runs the allocators on the current scenario. Allocation is a pure function of its
 * inputs, so it is a query keyed by (scenario, config, algorithms): changing a control
 * re-runs it, going back to earlier inputs is instant, and the previous result stays on
 * screen while the next one loads. Results are keyed by algorithm name.
 */
export function useAllocate({ scenario, config, algorithms, includeTrace = false, enabled = true }: AllocateArgs) {
  return useQuery({
    queryKey: ['allocate', scenario, config, algorithms, includeTrace],
    queryFn: () => {
      if (!scenario) throw new Error('No scenario to allocate')
      return api.allocate({ scenario, config, algorithms, include_trace: includeTrace })
    },
    enabled: enabled && scenario !== undefined && algorithms.length > 0,
    staleTime: Infinity,
    placeholderData: keepPreviousData,
  })
}
