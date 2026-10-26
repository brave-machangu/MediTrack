import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { resetMockLogs } from '../mocks/handlers'
import { server } from '../mocks/server'

// The first test in a file pays for imports and MSW start-up (about 2 s here, more on a busy machine).
// These are upper limits, not waits: a missing element still fails, just after 5 s instead of 1 s.
configure({ asyncUtilTimeout: 5000 })

// jsdom starts from a blank document; mirror index.html so axe checks what users actually get.
document.documentElement.lang = 'en-GB'

// A request with no handler is a test bug, not something to let through to the network.
beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
})

afterEach(() => {
  cleanup()
  server.resetHandlers()
  resetMockLogs()
})

afterAll(() => {
  server.close()
})
