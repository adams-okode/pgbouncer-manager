import { useCapacity } from '../hooks/useCapacity'
import type { CapacityStatus, TargetCapacity } from '../types'

const STATUS_STYLES: Record<CapacityStatus, string> = {
  ok: 'bg-green-100 text-green-800',
  tight: 'bg-yellow-100 text-yellow-800',
  oversubscribed: 'bg-red-100 text-red-800',
  unknown: 'bg-gray-100 text-gray-600',
}

export function CapacityPanel() {
  const { data, isLoading, error } = useCapacity()
  const targets = data?.targets ?? []

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Connection Capacity</h3>
        <p className="text-sm text-gray-500">
          Server connections committed to each target Postgres.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          Failed to load capacity: {error.message}
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Loading…</p>}

      {!isLoading && !error && targets.length === 0 && (
        <p className="text-sm text-gray-500">No tenants configured yet.</p>
      )}

      <div className="space-y-3">
        {targets.map((target) => (
          <TargetRow key={`${target.host}:${target.port}`} target={target} />
        ))}
      </div>
    </div>
  )
}

function TargetRow({ target }: { target: TargetCapacity }) {
  const tenantCount = target.tenants.length
  return (
    <div className="bg-white shadow rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-gray-900">
          {target.host}:{target.port}
        </span>
        <span
          className={`px-2 py-0.5 text-xs font-semibold rounded-full ${STATUS_STYLES[target.status]}`}
        >
          {target.status}
        </span>
      </div>

      <div className="text-sm text-gray-600">
        <span className="font-semibold text-gray-900">{target.worst_case_total}</span> connections
        committed across {tenantCount} {tenantCount === 1 ? 'pool' : 'pools'}
        {target.max_connections !== null && <> of {target.max_connections} max</>}
        {target.headroom !== null && (
          <>
            {' · '}
            <span className={target.headroom < 0 ? 'text-red-700 font-semibold' : ''}>
              {target.headroom < 0
                ? `${Math.abs(target.headroom)} over capacity`
                : `${target.headroom} spare`}
            </span>
          </>
        )}
      </div>

      {target.status === 'unknown' && (
        <p className="text-xs text-gray-500">
          Set CAPACITY_LIMITS for {target.host}:{target.port} to enable a verdict.
        </p>
      )}

      {target.unbounded_pools.length > 0 && (
        <p className="text-xs text-yellow-700">
          No forced user on {target.unbounded_pools.join(', ')} — PgBouncer opens a pool per
          connecting user, so the real total can exceed this.
        </p>
      )}
    </div>
  )
}
