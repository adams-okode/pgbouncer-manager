import { ExclamationTriangleIcon, InfoCircledIcon } from '@radix-ui/react-icons'
import {
  Badge,
  Callout,
  Card,
  Code,
  Flex,
  Grid,
  Heading,
  Progress,
  Separator,
  Skeleton,
  Text,
} from '@radix-ui/themes'

import { useCapacity } from '../hooks/useCapacity'
import type { CapacityStatus, TargetCapacity } from '../types'

type BadgeColor = 'green' | 'amber' | 'red' | 'gray'

const STATUS_COLOR: Record<CapacityStatus, BadgeColor> = {
  ok: 'green',
  tight: 'amber',
  oversubscribed: 'red',
  unknown: 'gray',
}

const STATUS_LABEL: Record<CapacityStatus, string> = {
  ok: 'OK',
  tight: 'Tight',
  oversubscribed: 'Oversubscribed',
  unknown: 'Unknown',
}

export function CapacityPanel() {
  const { data, isLoading, error } = useCapacity()
  const targets = data?.targets ?? []

  return (
    <Flex direction="column" gap="3">
      <Flex direction="column" gap="1">
        <Heading size="4">Connection Capacity</Heading>
        <Text size="2" color="gray">
          Server connections committed to each target Postgres. Pool sizes add up across
          tenants pointing at the same server.
        </Text>
      </Flex>

      {error && (
        <Callout.Root color="red" role="alert">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>Failed to load capacity: {error.message}</Callout.Text>
        </Callout.Root>
      )}

      {isLoading && (
        <Card size="2">
          <Skeleton>
            <Text size="2">Loading capacity for every configured target…</Text>
          </Skeleton>
        </Card>
      )}

      {!isLoading && !error && targets.length === 0 && (
        <Card size="2">
          <Text size="2" color="gray">
            No tenants configured yet.
          </Text>
        </Card>
      )}

      <Flex direction="column" gap="3">
        {targets.map((target) => (
          <TargetRow key={`${target.host}:${target.port}`} target={target} />
        ))}
      </Flex>
    </Flex>
  )
}

function TargetRow({ target }: { target: TargetCapacity }) {
  const tenantCount = target.tenants.length
  const pct = target.utilization === null ? null : Math.round(target.utilization * 100)

  return (
    <Card size="2">
      <Flex direction="column" gap="3">
        <Flex align="center" justify="between" gap="3" wrap="wrap">
          <Code size="3" variant="ghost" weight="medium">
            {target.host}:{target.port}
          </Code>
          <Flex align="center" gap="2">
            <Badge color="gray" variant="soft" title="Where the pool sizes were read from">
              via {target.source}
            </Badge>
            <Badge color={STATUS_COLOR[target.status]} variant="soft">
              {STATUS_LABEL[target.status]}
            </Badge>
          </Flex>
        </Flex>

        {pct !== null && (
          <Flex direction="column" gap="1">
            <Progress
              value={Math.min(pct, 100)}
              color={STATUS_COLOR[target.status] === 'gray' ? undefined : STATUS_COLOR[target.status]}
              size="2"
            />
            <Text size="1" color="gray">
              {pct}% of usable connections committed
            </Text>
          </Flex>
        )}

        <Separator size="4" />

        <Grid columns={{ initial: '2', sm: '4' }} gap="3">
          <Metric
            label="Committed"
            value={String(target.worst_case_total)}
            hint={
              target.reserve_total > 0
                ? `${target.declared_total} pool + ${target.reserve_total} reserve`
                : `across ${tenantCount} ${tenantCount === 1 ? 'pool' : 'pools'}`
            }
          />
          <Metric
            label="Server max"
            value={target.max_connections === null ? '—' : String(target.max_connections)}
            hint={target.max_connections === null ? 'Not configured' : 'From CAPACITY_LIMITS'}
          />
          <Metric
            label={target.headroom !== null && target.headroom < 0 ? 'Over by' : 'Spare'}
            value={target.headroom === null ? '—' : String(Math.abs(target.headroom))}
            hint={target.headroom === null ? 'Needs a limit' : 'After superuser reserve'}
            color={
              target.headroom === null ? undefined : target.headroom < 0 ? 'red' : undefined
            }
          />
          <Metric label="Tenants" value={String(tenantCount)} hint={target.tenants.join(', ')} />
        </Grid>

        {target.status === 'unknown' && (
          <Callout.Root color="gray" variant="surface" size="1">
            <Callout.Icon>
              <InfoCircledIcon />
            </Callout.Icon>
            <Callout.Text>
              Set <Code>CAPACITY_LIMITS</Code> for{' '}
              <Code>
                {target.host}:{target.port}
              </Code>{' '}
              to get a verdict instead of raw totals.
            </Callout.Text>
          </Callout.Root>
        )}

        {target.unbounded_pools.length > 0 && (
          <Callout.Root color="amber" variant="surface" size="1">
            <Callout.Icon>
              <ExclamationTriangleIcon />
            </Callout.Icon>
            <Callout.Text>
              No forced user on {target.unbounded_pools.join(', ')} — PgBouncer opens a pool per
              connecting user, so the real total can exceed what is shown here.
            </Callout.Text>
          </Callout.Root>
        )}
      </Flex>
    </Card>
  )
}

interface MetricProps {
  label: string
  value: string
  hint?: string
  color?: 'red'
}

function Metric({ label, value, hint, color }: MetricProps) {
  return (
    <Flex direction="column" gap="1" minWidth="0">
      <Text size="1" color="gray">
        {label}
      </Text>
      <Text size="5" weight="bold" color={color} highContrast={!color}>
        {value}
      </Text>
      {hint && (
        <Text size="1" color="gray" truncate title={hint}>
          {hint}
        </Text>
      )}
    </Flex>
  )
}
