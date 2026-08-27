import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Theme } from '@radix-ui/themes'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* Pinned to light: dark mode needs a `.dark-theme` class toggle that
          nothing here drives yet, and inheriting would leave the hardcoded
          --gray-2 page background mismatched against dark panels. */}
      <Theme appearance="light" accentColor="indigo" grayColor="slate" radius="medium">
        <App />
      </Theme>
    </QueryClientProvider>
  </React.StrictMode>,
)
