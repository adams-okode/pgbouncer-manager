import type { ReactNode } from 'react'

import { useDashboard } from '../hooks/useDashboard'
import { CapacityPanel } from './CapacityPanel'

export function Dashboard() {
  const { totalTenants, activeConnections, waiting, utilization, isLoading, error } =
    useDashboard()

  const fmt = (n: number) => (isLoading ? '…' : String(n))

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          Failed to load dashboard data: {error.message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Total Tenants" value={fmt(totalTenants)} icon={iconUsers} />
        <Card label="Active Connections" value={fmt(activeConnections)} icon={iconBolt} />
        <Card
          label="Pool Utilization"
          value={isLoading ? '…' : `${utilization}%`}
          icon={iconChart}
        />
        <Card label="Waiting Connections" value={fmt(waiting)} icon={iconClock} />
      </div>

      <CapacityPanel />
    </div>
  )
}

function Card({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">{icon}</div>
          <div className="ml-5">
            <p className="text-sm font-medium text-gray-500 truncate">{label}</p>
            <p className="text-2xl font-semibold text-gray-900">{value}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

const iconClass = 'h-6 w-6 text-gray-400'

const iconUsers = (
  <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
  </svg>
)

const iconBolt = (
  <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
)

const iconChart = (
  <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
)

const iconClock = (
  <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
)
