import { defineConfig, devices } from '@playwright/test'

const port = 5174

// Screenshots for pull requests (DESIGN.md self-review): the app runs against the MSW mocks.
export default defineConfig({
  testDir: './screenshots',
  outputDir: './test-results',
  reporter: 'list',
  // A fixed browser timezone that differs from the demo patients', so screenshots are repeatable.
  use: { baseURL: `http://localhost:${port}`, timezoneId: 'Europe/London' },
  webServer: {
    command: `npm run dev:mock -- --port ${port} --strictPort`,
    url: `http://localhost:${port}`,
    reuseExistingServer: false,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
