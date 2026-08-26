// Types mirror the FastAPI backend response shapes.

export interface Tenant {
  id: string
  host: string
  port: number
  db_name: string
  user: string
  pool_size: number
  pool_mode?: string | null
}

// Payload for creating a tenant (password required).
export interface TenantForm {
  id: string
  host: string
  port: number
  db_name: string
  user: string
  password: string
  pool_size: number
  pool_mode?: string
}

// Partial update payload: every field optional.
export interface TenantUpdate {
  host?: string
  port?: number
  db_name?: string
  user?: string
  password?: string
  pool_size?: number
  pool_mode?: string
}

// SHOW POOLS row as normalized by the backend.
export interface PoolStatus {
  database: string
  user: string
  pool_mode: string
  active: number
  waiting: number
  idle: number
  max_wait: number
}

export interface PoolsResponse {
  pools: PoolStatus[]
}

// SHOW STATS rows are returned verbatim (column name -> value).
export type StatRow = Record<string, string>

export interface StatsResponse {
  stats: StatRow[]
}

export interface ReloadResponse {
  status: string
  message: string
}

export interface DeleteResponse {
  message: string
  id: string
}

export type CapacityStatus = 'ok' | 'tight' | 'oversubscribed' | 'unknown'

export interface TargetCapacity {
  host: string
  port: number
  tenants: string[]
  declared_total: number
  reserve_total: number
  worst_case_total: number
  current_connections: number | null
  max_connections: number | null
  headroom: number | null
  utilization: number | null
  status: CapacityStatus
  source: string
  unbounded_pools: string[]
}

export interface CapacityResponse {
  targets: TargetCapacity[]
}
