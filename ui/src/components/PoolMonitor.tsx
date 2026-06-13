import { usePools, useReload } from '../hooks/usePools'

export function PoolMonitor() {
  const { data, isLoading, error, refetch, isFetching } = usePools()
  const reload = useReload()
  const pools = data?.pools ?? []

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Pool Monitor</h2>
        <div className="space-x-3">
          <button
            onClick={() => reload.mutate()}
            disabled={reload.isPending}
            className="px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50"
          >
            {reload.isPending ? 'Reloading…' : 'Reload PgBouncer'}
          </button>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isFetching ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          Failed to load pools: {error.message}
        </div>
      )}
      {reload.error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          Reload failed: {reload.error.message}
        </div>
      )}
      {reload.isSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
          {reload.data.message}
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Database</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mode</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Active</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Waiting</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Idle</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Max Wait (s)</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">Loading…</td>
              </tr>
            ) : pools.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">No active pools.</td>
              </tr>
            ) : (
              pools.map((p) => (
                <tr key={`${p.database}:${p.user}`}>
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{p.database}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{p.user}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{p.pool_mode}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-700">{p.active}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-700">{p.waiting}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-700">{p.idle}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-700">{p.max_wait}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
