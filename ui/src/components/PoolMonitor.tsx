import {
  CheckCircledIcon,
  ExclamationTriangleIcon,
  ReloadIcon,
  UpdateIcon,
} from '@radix-ui/react-icons'
import {
  Badge,
  Button,
  Callout,
  Code,
  Flex,
  Heading,
  Table,
  Text,
} from '@radix-ui/themes'

import { usePools, useReload } from '../hooks/usePools'

export function PoolMonitor() {
  const { data, isLoading, error, refetch, isFetching } = usePools()
  const reload = useReload()
  const pools = data?.pools ?? []

  return (
    <Flex direction="column" gap="5">
      <Flex align="center" justify="between" gap="3" wrap="wrap">
        <Flex direction="column" gap="1">
          <Heading size="6">Pool Monitor</Heading>
          <Text size="2" color="gray">
            Live <Code>SHOW POOLS</Code> output from the PgBouncer admin console.
          </Text>
        </Flex>
        <Flex gap="3">
          <Button variant="soft" onClick={() => refetch()} loading={isFetching}>
            <UpdateIcon /> Refresh
          </Button>
          <Button color="amber" onClick={() => reload.mutate()} loading={reload.isPending}>
            <ReloadIcon /> Reload PgBouncer
          </Button>
        </Flex>
      </Flex>

      {error && (
        <Callout.Root color="red" role="alert">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>Failed to load pools: {error.message}</Callout.Text>
        </Callout.Root>
      )}
      {reload.error && (
        <Callout.Root color="red" role="alert">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>Reload failed: {reload.error.message}</Callout.Text>
        </Callout.Root>
      )}
      {reload.isSuccess && (
        <Callout.Root color="green" role="status">
          <Callout.Icon>
            <CheckCircledIcon />
          </Callout.Icon>
          <Callout.Text>{reload.data.message}</Callout.Text>
        </Callout.Root>
      )}

      <Table.Root variant="surface">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeaderCell>Database</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell>User</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell>Mode</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Active</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Waiting</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Idle</Table.ColumnHeaderCell>
            <Table.ColumnHeaderCell align="right">Max Wait (s)</Table.ColumnHeaderCell>
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
          ) : pools.length === 0 ? (
            <Table.Row>
              <Table.Cell colSpan={7}>
                <Text size="2" color="gray">
                  No active pools.
                </Text>
              </Table.Cell>
            </Table.Row>
          ) : (
            pools.map((p) => (
              <Table.Row key={`${p.database}:${p.user}`} align="center">
                <Table.RowHeaderCell>
                  <Text weight="medium">{p.database}</Text>
                </Table.RowHeaderCell>
                <Table.Cell>{p.user}</Table.Cell>
                <Table.Cell>
                  <Badge color="gray" variant="soft">
                    {p.pool_mode}
                  </Badge>
                </Table.Cell>
                <Table.Cell align="right">{p.active}</Table.Cell>
                <Table.Cell align="right">
                  {/* Waiting clients mean the pool is saturated, so make a
                      non-zero value impossible to skim past. */}
                  <Text color={p.waiting > 0 ? 'amber' : undefined} weight={p.waiting > 0 ? 'bold' : undefined}>
                    {p.waiting}
                  </Text>
                </Table.Cell>
                <Table.Cell align="right">{p.idle}</Table.Cell>
                <Table.Cell align="right">
                  <Text color={p.max_wait > 0 ? 'amber' : undefined}>{p.max_wait}</Text>
                </Table.Cell>
              </Table.Row>
            ))
          )}
        </Table.Body>
      </Table.Root>
    </Flex>
  )
}
