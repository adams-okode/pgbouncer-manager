import type {
  CapacityResponse,
  DeleteResponse,
  PoolsResponse,
  ReloadResponse,
  StatsResponse,
  Tenant,
  TenantForm,
  TenantUpdate,
} from '../types'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    ...options,
  })

  if (!res.ok) {
    let detail: string = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // response had no JSON body
    }
    throw new Error(`${res.status} ${detail}`)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  listTenants: () => request<Tenant[]>('/tenants'),
  getTenant: (id: string) => request<Tenant>(`/tenants/${id}`),
  addTenant: (data: TenantForm) =>
    request<Tenant>('/tenants', { method: 'POST', body: JSON.stringify(data) }),
  updateTenant: (id: string, data: TenantUpdate) =>
    request<Tenant>(`/tenants/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTenant: (id: string) =>
    request<DeleteResponse>(`/tenants/${id}`, { method: 'DELETE' }),
  listPools: () => request<PoolsResponse>('/pools/status'),
  listStats: () => request<StatsResponse>('/pools/stats'),
  reload: () => request<ReloadResponse>('/pools/reload', { method: 'POST' }),
  getCapacity: () => request<CapacityResponse>('/capacity'),
}
