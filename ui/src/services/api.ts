export const api = {
  listTenants: async () => fetch('/api/tenants').then(r => r.json()),
  getTenant: (id: string) => fetch(`/api/tenants/${id}`).then(r => r.json()),
  addTenant: (data: any) => fetch('/api/tenants', { method: 'POST', body: JSON.stringify(data) }).then(r => r.json()),
  updateTenant: (id: string, data: any) => fetch(`/api/tenants/${id}`, { method: 'PATCH', body: JSON.stringify(data) }).then(r => r.json()),
  deleteTenant: (id: string) => fetch(`/api/tenants/${id}`, { method: 'DELETE' }).then(r => r.json()),
  listPools: async () => fetch('/api/pools/status').then(r => r.json()),
  listStats: async () => fetch('/api/pools/stats').then(r => r.json()),
  reload: async () => fetch('/api/pools/reload', { method: 'POST' }).then(r => r.json()),
}
