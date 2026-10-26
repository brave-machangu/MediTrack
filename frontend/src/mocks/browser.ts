import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'
import { scenarios } from './scenarios'

export async function startMockWorker(scenario: string | null) {
  const extra = scenario === null ? [] : (scenarios[scenario]?.() ?? [])
  // Requests the mocks don't cover (scripts, styles, icons) go to the dev server as usual.
  await setupWorker(...extra, ...handlers).start({ onUnhandledFrame: 'bypass' })
}
