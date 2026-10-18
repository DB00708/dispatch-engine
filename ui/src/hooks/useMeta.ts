import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

/** Fetched once: algorithm list, fault types, available estimators, defaults and limits. */
export function useMeta() {
  return useQuery({ queryKey: ['meta'], queryFn: api.meta, staleTime: Infinity })
}
