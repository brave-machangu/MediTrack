import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './client'

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // One quick retry covers a blip in the connection. Asking again won't change a 4xx answer,
        // and a long retry chain would keep an older user waiting before they see what went wrong.
        retry: (failureCount, error) =>
          failureCount < 1 && !(error instanceof ApiError && error.status !== undefined && error.status < 500),
      },
    },
  })
}
