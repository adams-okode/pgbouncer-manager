import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../services/api'
import type { TenantForm, TenantUpdate } from '../types'

const TENANTS_KEY = ['tenants'] as const

export function useTenants() {
  return useQuery({ queryKey: TENANTS_KEY, queryFn: api.listTenants })
}

export function useAddTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TenantForm) => api.addTenant(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: TENANTS_KEY }),
  })
}

export function useUpdateTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TenantUpdate }) =>
      api.updateTenant(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: TENANTS_KEY }),
  })
}

export function useDeleteTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteTenant(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: TENANTS_KEY }),
  })
}
