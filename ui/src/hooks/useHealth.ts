import { useQuery } from '@tanstack/react-query'

import { api } from '../services/api'

const HEALTH_KEY = ['health'] as const

export function useHealth() {
  return useQuery({
    queryKey: HEALTH_KEY,
    queryFn: api.getHealth,
    // The mode is fixed for the life of the process it is talking to.
    staleTime: Infinity,
  })
}

/**
 * Whether this backend refuses config writes.
 *
 * True under the Kubernetes operator, where the custom resources are the
 * source of truth and anything written here would be reverted on the next
 * reconcile. Defaults to false while loading so the UI does not flicker into
 * a read-only state on a slow first request.
 */
export function useReadOnly(): boolean {
  return useHealth().data?.read_only ?? false
}
