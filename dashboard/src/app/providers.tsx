'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState, type ReactNode } from 'react';
import { api } from '@/lib/api';

export function Providers({ children }: { children: ReactNode }) {
  const [sessionReady, setSessionReady] = useState(false);
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  useEffect(() => {
    api.restoreSession();
    setSessionReady(true);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {sessionReady ? children : null}
    </QueryClientProvider>
  );
}
