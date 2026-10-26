import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { resetMockData } from '../mocks/handlers'
import { server } from '../mocks/server'

// The first test in a file pays for imports and MSW start-up (about 2 s here, more on a busy machine).
// These are upper limits, not waits: a missing element still fails, just after 5 s instead of 1 s.
configure({ asyncUtilTimeout: 5000 })

// jsdom starts from a blank document; mirror index.html so axe checks what users actually get.
document.documentElement.lang = 'en-GB'

// jsdom 30 has no HTMLDialogElement.showModal() or close(). This stand-in only toggles `open`; focus trapping,
// Esc and the backdrop are the browser's job and are checked in Playwright (screenshots/medications.spec.ts).
if (typeof HTMLDialogElement.prototype.showModal !== 'function') {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute('open')
  }
}

// A request with no handler is a test bug, not something to let through to the network.
beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' })
})

afterEach(() => {
  cleanup()
  server.resetHandlers()
  resetMockData()
})

afterAll(() => {
  server.close()
})
