import { useState } from 'react'
import { ExclamationTriangleIcon, PlusIcon } from '@radix-ui/react-icons'
import {
  AlertDialog,
  Badge,
  Button,
  Callout,
  Code,
  Dialog,
  Flex,
  Heading,
  Table,
  Text,
  TextField,
} from '@radix-ui/themes'

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
  const [pendingDelete, setPendingDelete] = useState<Tenant | null>(null)

  const closeModal = () => setModal({ mode: 'closed' })
  const editing = modal.mode === 'edit' ? modal.tenant : null

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

  const confirmDelete = () => {
    if (!pendingDelete) return
    deleteTenant.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
  }

  // Add/update failures surface inside the dialog, which covers the page while
  // they happen; only delete failures need a page-level callout.
  const formError = modal.mode === 'add' ? addTenant.error : updateTenant.error
  const saving = addTenant.isPending || updateTenant.isPending

  return (
    <Flex direction="column" gap="5">
      <Flex align="center" justify="between" gap="3" wrap="wrap">
        <Flex direction="column" gap="1">
          <Heading size="6">Tenants</Heading>
          <Text size="2" color="gray">
            Each row is one <Code>databases.ini</Code> entry and its own PgBouncer pool.
          </Text>
        </Flex>
        <Button onClick={() => setModal({ mode: 'add' })}>
          <PlusIcon /> Add Tenant
        </Button>
      </Flex>

      {error && (
        <Callout.Root color="red" role="alert">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>Failed to load tenants: {error.message}</Callout.Text>
        </Callout.Root>
      )}
      {deleteTenant.error && (
        <Callout.Root color="red" role="alert">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>{deleteTenant.error.message}</Callout.Text>
        </Callout.Root>
      )}

      <Table.Root variant="surface">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeaderCell>ID</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell>Host</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Port</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell>Database</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell>User</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Pool Size</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Actions</Table.ColumnHeaderCell>
          </Table.Row>
        </Table.Header>

        <Table.Body>
          {isLoading ? (
            <Table.Row>
              <Table.Cell colSpan={7}>
                <Text size="2" color="gray">
                  Loading…
                </Text>
              </Table.Cell>
            </Table.Row>
          ) : tenants.length === 0 ? (
            <Table.Row>
              <Table.Cell colSpan={7}>
                <Text size="2" color="gray">
                  No tenants yet. Use “Add Tenant” to create one.
                </Text>
              </Table.Cell>
            </Table.Row>
          ) : (
            tenants.map((t) => (
              <Table.Row key={t.id} align="center">
                <Table.RowHeaderCell>
                  <Text weight="medium">{t.id}</Text>
                </Table.RowHeaderCell>
                <Table.Cell>
                  <Code variant="ghost">{t.host}</Code>
                </Table.Cell>
                <Table.Cell align="right">{t.port}</Table.Cell>
                <Table.Cell>{t.db_name}</Table.Cell>
                <Table.Cell>{t.user}</Table.Cell>
                <Table.Cell align="right">
                  <Badge color="gray" variant="soft">
                    {t.pool_size}
                  </Badge>
                </Table.Cell>
                <Table.Cell align="right">
                  <Flex gap="2" justify="end">
                    <Button
                      size="1"
                      variant="soft"
                      onClick={() => setModal({ mode: 'edit', tenant: t })}
                    >
                      Edit
                    </Button>
                    <Button
                      size="1"
                      variant="soft"
                      color="red"
                      onClick={() => setPendingDelete(t)}
                    >
                      Delete
                    </Button>
                  </Flex>
                </Table.Cell>
              </Table.Row>
            ))
          )}
        </Table.Body>
      </Table.Root>

      <Dialog.Root
        open={modal.mode !== 'closed'}
        onOpenChange={(open) => {
          if (!open) closeModal()
        }}
      >
        <Dialog.Content maxWidth="460px">
          <Dialog.Title>{editing ? `Edit ${editing.id}` : 'Add Tenant'}</Dialog.Title>
          <Dialog.Description size="2" color="gray" mb="4">
            {editing
              ? 'Leave the password blank to keep the stored credential.'
              : 'The password is hashed before it reaches userlist.txt and is never stored in plaintext.'}
          </Dialog.Description>

          <form onSubmit={handleSubmit}>
            <Flex direction="column" gap="3">
              {formError && (
                <Callout.Root color="red" size="1" role="alert">
                  <Callout.Icon>
                    <ExclamationTriangleIcon />
                  </Callout.Icon>
                  <Callout.Text>{formError.message}</Callout.Text>
                </Callout.Root>
              )}

              {!editing && (
                <Field label="Tenant ID" name="id" required placeholder="tenant1" />
              )}
              <Field
                label="Database Host"
                name="host"
                required
                placeholder="db.example.com"
                defaultValue={editing?.host ?? ''}
              />
              <Field
                label="Port"
                name="port"
                type="number"
                defaultValue={editing ? String(editing.port) : '5432'}
              />
              <Field
                label="Database Name"
                name="db_name"
                defaultValue={editing?.db_name ?? 'postgres'}
              />
              <Field
                label="Database User"
                name="user"
                defaultValue={editing?.user ?? 'postgres'}
              />
              <Field
                label={editing ? 'New Password' : 'Database Password'}
                name="password"
                type="password"
                required={!editing}
                placeholder={editing ? 'Unchanged' : ''}
              />
              <Field
                label="Pool Size"
                name="pool_size"
                type="number"
                hint="Server connections this pool may open. Sizes add up per target."
                defaultValue={editing ? String(editing.pool_size) : '15'}
              />

              <Flex gap="3" justify="end" mt="2">
                <Dialog.Close>
                  <Button type="button" variant="soft" color="gray">
                    Cancel
                  </Button>
                </Dialog.Close>
                <Button type="submit" loading={saving}>
                  {editing ? 'Save Changes' : 'Add Tenant'}
                </Button>
              </Flex>
            </Flex>
          </form>
        </Dialog.Content>
      </Dialog.Root>

      <AlertDialog.Root
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null)
        }}
      >
        <AlertDialog.Content maxWidth="440px">
          <AlertDialog.Title>Delete {pendingDelete?.id}?</AlertDialog.Title>
          <AlertDialog.Description size="2">
            This removes the <Code>databases.ini</Code> entry and drops its credential from{' '}
            <Code>userlist.txt</Code>, unless another tenant still uses that user. Existing
            clients routed through this pool will fail to reconnect.
          </AlertDialog.Description>

          <Flex gap="3" justify="end" mt="4">
            <AlertDialog.Cancel>
              <Button variant="soft" color="gray">
                Cancel
              </Button>
            </AlertDialog.Cancel>
            <Button color="red" loading={deleteTenant.isPending} onClick={confirmDelete}>
              Delete tenant
            </Button>
          </Flex>
        </AlertDialog.Content>
      </AlertDialog.Root>
    </Flex>
  )
}

interface FieldProps {
  label: string
  name: string
  type?: React.ComponentProps<typeof TextField.Root>['type']
  required?: boolean
  defaultValue?: string
  placeholder?: string
  hint?: string
}

function Field({
  label,
  name,
  type = 'text',
  required,
  defaultValue,
  placeholder,
  hint,
}: FieldProps) {
  return (
    <Flex direction="column" gap="1" asChild>
      <label>
        <Text size="2" weight="medium">
          {label}
        </Text>
        <TextField.Root
          type={type}
          name={name}
          required={required}
          defaultValue={defaultValue}
          placeholder={placeholder}
        />
        {hint && (
          <Text size="1" color="gray">
            {hint}
          </Text>
        )}
      </label>
    </Flex>
  )
}
