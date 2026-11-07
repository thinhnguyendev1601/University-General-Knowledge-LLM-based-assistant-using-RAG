/**
 * App — root component: providers + router.
 */
import { BrowserRouter } from 'react-router-dom'
import { AppProviders } from './providers'
import { AppRouter } from './router'
import { AuthBootstrap } from '@/features/auth'

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AuthBootstrap>
          <AppRouter />
        </AuthBootstrap>
      </BrowserRouter>
    </AppProviders>
  )
}
