import { useTenants } from './useTenants'
import { usePools } from './usePools'

export function useDashboard() {
  const tenants = useTenants()
  const pools = usePools()

  const poolList = pools.data?.pools ?? []
  const active = poolList.reduce((sum, p) => sum + p.active, 0)
  const waiting = poolList.reduce((sum, p) => sum + p.waiting, 0)
  const idle = poolList.reduce((sum, p) => sum + p.idle, 0)
  const totalConnections = active + waiting + idle
  const utilization = totalConnections
    ? Math.round((active / totalConnections) * 100)
    : 0

  return {
    totalTenants: tenants.data?.length ?? 0,
    activeConnections: active,
    waiting,
    idle,
    utilization,
    isLoading: tenants.isLoading || pools.isLoading,
    error: (tenants.error ?? pools.error) as Error | null,
  }
}
