import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../services/api'

const POOLS_KEY = ['pools'] as const

export function usePools() {
  return useQuery({
    queryKey: POOLS_KEY,
    queryFn: api.listPools,
    refetchInterval: 5000,
  })
}

export function useReload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.reload(),
    onSuccess: () => qc.invalidateQueries({ queryKey: POOLS_KEY }),
  })
}
