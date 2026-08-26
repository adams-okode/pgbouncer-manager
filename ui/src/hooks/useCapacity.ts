import { useQuery } from '@tanstack/react-query'

import { api } from '../services/api'

export function useCapacity() {
  return useQuery({
    queryKey: ['capacity'] as const,
    queryFn: api.getCapacity,
    refetchInterval: 15000,
  })
}
