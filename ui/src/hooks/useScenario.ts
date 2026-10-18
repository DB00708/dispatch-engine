import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { GenerateRequest } from '../api/models'

/**
 * The generated scenario for a seed and counts. Generation is deterministic, so it is
 * cached like a query; the page copies it into React state when the user edits it.
 */
export function useScenario(params: GenerateRequest) {
  return useQuery({
    queryKey: ['scenario', params],
    queryFn: () => api.generate(params),
    staleTime: Infinity,
    placeholderData: keepPreviousData,
  })
}
