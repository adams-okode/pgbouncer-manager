import { useState } from 'react'

import {
  useAddTenant,
  useDeleteTenant,
  useTenants,
  useUpdateTenant,
} from '../hooks/useTenants'
import type { Tenant, TenantForm } from '../types'

type ModalState =
  | { mode: 'closed' }
  | { mode: 'add' }
  | { mode: 'edit'; tenant: Tenant }

export function TenantTable() {
  const { data: tenants = [], isLoading, error } = useTenants()
  const addTenant = useAddTenant()
  const updateTenant = useUpdateTenant()
  const deleteTenant = useDeleteTenant()
  const [modal, setModal] = useState<ModalState>({ mode: 'closed' })

  const closeModal = () => setModal({ mode: 'closed' })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const password = (fd.get('password') as string) || ''
    const base = {
      host: fd.get('host') as string,
      port: Number(fd.get('port')) || 5432,
      db_name: (fd.get('db_name') as string) || 'postgres',
      user: (fd.get('user') as string) || 'postgres',
      pool_size: Number(fd.get('pool_size')) || 15,
    }

    if (modal.mode === 'add') {
      const payload: TenantForm = { id: fd.get('id') as string, password, ...base }
      addTenant.mutate(payload, { onSuccess: closeModal })
    } else if (modal.mode === 'edit') {
      updateTenant.mutate(
        { id: modal.tenant.id, data: { ...base, ...(password ? { password } : {}) } },
        { onSuccess: closeModal },
      )
    }
  }

  const handleDelete = (id: string) => {
    if (window.confirm(`Delete tenant "${id}"? This removes its database and credential.`)) {
      deleteTenant.mutate(id)
    }
  }

  const mutationError = addTenant.error || updateTenant.error || deleteTenant.error

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Tenants</h2>
        <button
          onClick={() => setModal({ mode: 'add' })}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Add Tenant
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          Failed to load tenants: {error.message}
        </div>
      )}
      {mutationError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {mutationError.message}
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {['ID', 'Host', 'Port', 'DB Name', 'User', 'Pool Size'].map((h) => (
                <th
                  key={h}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : tenants.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                  No tenants yet. Click “Add Tenant” to create one.
                </td>
              </tr>
            ) : (
              tenants.map((t) => (
                <tr key={t.id}>
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{t.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{t.host}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{t.port}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{t.db_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{t.user}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700">{t.pool_size}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right space-x-3">
                    <button
                      onClick={() => setModal({ mode: 'edit', tenant: t })}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(t.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modal.mode !== 'closed' && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {modal.mode === 'add' ? 'Add Tenant' : `Edit ${modal.tenant.id}`}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              {modal.mode === 'add' && (
                <Field label="Tenant ID" name="id" required />
              )}
              <Field
                label="Database Host"
                name="host"
                required
                defaultValue={modal.mode === 'edit' ? modal.tenant.host : ''}
              />
              <Field
                label="Port"
                name="port"
                type="number"
                defaultValue={modal.mode === 'edit' ? String(modal.tenant.port) : '5432'}
              />
              <Field
                label="Database Name"
                name="db_name"
                defaultValue={modal.mode === 'edit' ? modal.tenant.db_name : 'postgres'}
              />
              <Field
                label="Database User"
                name="user"
                defaultValue={modal.mode === 'edit' ? modal.tenant.user : 'postgres'}
              />
              <Field
                label={modal.mode === 'edit' ? 'New Password (leave blank to keep)' : 'Database Password'}
                name="password"
                type="password"
                required={modal.mode === 'add'}
              />
              <Field
                label="Pool Size"
                name="pool_size"
                type="number"
                defaultValue={modal.mode === 'edit' ? String(modal.tenant.pool_size) : '15'}
              />
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addTenant.isPending || updateTenant.isPending}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {modal.mode === 'add' ? 'Add Tenant' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

interface FieldProps {
  label: string
  name: string
  type?: string
  required?: boolean
  defaultValue?: string
}

function Field({ label, name, type = 'text', required, defaultValue }: FieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        type={type}
        name={name}
        required={required}
        defaultValue={defaultValue}
        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
      />
    </div>
  )
}
