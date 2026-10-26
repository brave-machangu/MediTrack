import react from '@vitejs/plugin-react'
import { msw } from 'msw/vite'
import { defineConfig } from 'vitest/config'

const backend = 'http://localhost:8000'

export default defineConfig(({ mode }) => ({
  // `npm run dev:mock` serves the MSW worker script; production builds never include it.
  plugins: [react(), ...(mode === 'mock' ? [msw({ mode: 'worker-only' })] : [])],
  server: {
    // copy.test.ts checks the disclaimer and demo banner against docs/requirements.md.
    fs: { allow: ['.', '../docs'] },
    proxy: {
      '/api': backend,
      '/healthz': backend,
      '/readyz': backend,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    // Patient dates must never depend on the machine's timezone (AC-35).
    env: { TZ: 'Asia/Tokyo' },
    restoreMocks: true,
  },
}))
