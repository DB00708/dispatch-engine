import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'

/** The scarcity sweep runs only when the user presses Run, so it is a mutation. */
export function useSweep() {
  return useMutation({ mutationFn: api.sweep })
}
