import type { ReactNode } from 'react'
import {
  ActivityLogIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  LightningBoltIcon,
  PersonIcon,
} from '@radix-ui/react-icons'
import { Box, Callout, Card, Flex, Grid, Heading, Skeleton, Text } from '@radix-ui/themes'

import { useDashboard } from '../hooks/useDashboard'
import { CapacityPanel } from './CapacityPanel'

export function Dashboard() {
  const { totalTenants, activeConnections, waiting, utilization, isLoading, error } =
    useDashboard()

  return (
    <Flex direction="column" gap="6">
      <Heading size="6">Dashboard</Heading>

      {error && (
        <Callout.Root color="red" role="alert">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>Failed to load dashboard data: {error.message}</Callout.Text>
        </Callout.Root>
      )}

      <Grid columns={{ initial: '1', sm: '2', lg: '4' }} gap="4">
        <Stat
          label="Tenants"
          value={String(totalTenants)}
          hint="Entries in databases.ini"
          icon={<PersonIcon />}
          loading={isLoading}
        />
        <Stat
          label="Active Connections"
          value={String(activeConnections)}
          hint="Server connections running a query"
          icon={<LightningBoltIcon />}
          loading={isLoading}
        />
        <Stat
          label="Busy Share"
          value={`${utilization}%`}
          // Deliberately not "Pool Utilization": this is active / (active + idle
          // + waiting) across open connections, not usage against pool_size.
          // The Connection Capacity panel below is what tracks real headroom.
          hint="Of open connections, share not idle"
          icon={<ActivityLogIcon />}
          loading={isLoading}
          // Intentionally uncoloured: the denominator is open connections, so a
          // single busy connection reads 100% and would cry wolf. Real headroom
          // is the Connection Capacity panel below.
        />
        <Stat
          label="Waiting"
          value={String(waiting)}
          hint="Clients queued for a connection"
          icon={<ClockIcon />}
          loading={isLoading}
          color={waiting > 0 ? 'amber' : undefined}
        />
      </Grid>

      <CapacityPanel />
    </Flex>
  )
}

interface StatProps {
  label: string
  value: string
  hint: string
  icon: ReactNode
  loading: boolean
  color?: 'red' | 'amber'
}

function Stat({ label, value, hint, icon, loading, color }: StatProps) {
  return (
    <Card size="2">
      <Flex direction="column" gap="2">
        <Flex align="center" gap="2" style={{ color: 'var(--gray-a10)' }}>
          {icon}
          <Text size="2" weight="medium" color="gray">
            {label}
          </Text>
        </Flex>

        <Skeleton loading={loading}>
          <Heading size="7" color={color} highContrast={!color}>
            {value}
          </Heading>
        </Skeleton>

        <Box>
          <Text size="1" color="gray">
            {hint}
          </Text>
        </Box>
      </Flex>
    </Card>
  )
}
