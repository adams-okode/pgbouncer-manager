export interface Tenant {
  id: string
  host: string
  port: number
  db_name: string
  user: string
  pool_size: number
}

export interface TenantForm {
  id: string
  host: string
  port: number
  db_name: string
  user: string
  password: string
  pool_size: number
}

export interface PoolStatus {
  database: string
  user: string
  pool_mode: string
  active: number
  waiting: number
  idle: number
  max_wait: number
}

export interface PoolStat {
  database: string
  user: string
  type: string
  state: string
  addr: string
  port: number
  local_addr: string
  local_port: number
  create_time: number
  connect_time: number
  receive_time: number
  send_time: number
  write_bytes: number
  read_bytes: number
  wait: number
  wait_us: number
}

export interface Stats {
  database: string
  user: string
  type: string
  state: string
  addr: string
  port: number
  local_addr: string
  local_port: number
  create_time: number
  connect_time: number
  receive_time: number
  send_time: number
  write_bytes: number
  read_bytes: number
  wait: number
}
