import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export async function startMockWorker() {
  // Requests the mocks don't cover (scripts, styles, icons) go to the dev server as usual.
  await setupWorker(...handlers).start({ onUnhandledFrame: 'bypass' })
}
