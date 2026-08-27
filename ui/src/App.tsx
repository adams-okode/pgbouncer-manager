import { Box, Container, Flex, Heading, Tabs, Text } from '@radix-ui/themes'

import { Dashboard } from './components/Dashboard'
import { PoolMonitor } from './components/PoolMonitor'
import { TenantTable } from './components/TenantTable'

function App() {
  return (
    <Flex direction="column" minHeight="100vh">
      <Box
        asChild
        style={{
          borderBottom: '1px solid var(--gray-a5)',
          backgroundColor: 'var(--color-panel-solid)',
        }}
      >
        <header>
          <Container size="4" px="5" py="4">
            <Heading size="5" weight="bold">
              PgBouncer Manager
            </Heading>
            <Text size="2" color="gray">
              Tenant routing, pool health, and connection budget
            </Text>
          </Container>
        </header>
      </Box>

      {/* Radix unmounts the inactive panels, so each tab's queries stay idle
          until it is opened. */}
      <Tabs.Root defaultValue="dashboard">
        <Box style={{ borderBottom: '1px solid var(--gray-a5)' }}>
          <Container size="4" px="5">
            <Tabs.List size="2" style={{ boxShadow: 'none' }}>
              <Tabs.Trigger value="dashboard">Dashboard</Tabs.Trigger>
              <Tabs.Trigger value="tenants">Tenants</Tabs.Trigger>
              <Tabs.Trigger value="pools">Pools</Tabs.Trigger>
            </Tabs.List>
          </Container>
        </Box>

        <Container size="4" px="5" py="6" asChild>
          <main>
            <Tabs.Content value="dashboard">
              <Dashboard />
            </Tabs.Content>
            <Tabs.Content value="tenants">
              <TenantTable />
            </Tabs.Content>
            <Tabs.Content value="pools">
              <PoolMonitor />
            </Tabs.Content>
          </main>
        </Container>
      </Tabs.Root>
    </Flex>
  )
}

export default App
