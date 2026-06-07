import { useState } from 'react'
import { TenantTable } from './components/TenantTable'
import { PoolMonitor } from './components/PoolMonitor'
import { Dashboard } from './components/Dashboard'

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tenants' | 'pools'>('dashboard')

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">PgBouncer Manager</h1>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  activeTab === 'dashboard'
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('tenants')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  activeTab === 'tenants'
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                Tenants
              </button>
              <button
                onClick={() => setActiveTab('pools')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  activeTab === 'pools'
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                Pools
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'tenants' && <TenantTable />}
        {activeTab === 'pools' && <PoolMonitor />}
      </main>
    </div>
  )
}

export default App
