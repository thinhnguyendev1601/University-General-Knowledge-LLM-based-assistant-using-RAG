/**
 * AppProviders — gom các provider dùng chung cho toàn app.
 * Theme được áp lên <html> ngay khi mount để khớp với state đã persist.
 */
import { useEffect, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useUIStore } from '@/hooks/useUIStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

interface AppProvidersProps {
  children: ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  const theme = useUIStore((state) => state.theme)

  // Script trong index.html đã set data-theme trước render để tránh FOUC;
  // effect này giữ DOM đồng bộ khi state đổi sau đó.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
