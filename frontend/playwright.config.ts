import { defineConfig, devices } from '@playwright/test'

const port = 5174

// Screenshots for pull requests (DESIGN.md self-review): the app runs against the MSW mocks.
export default defineConfig({
  testDir: './screenshots',
  outputDir: './test-results',
  reporter: 'list',
  use: { baseURL: `http://localhost:${port}` },
  webServer: {
    command: `npm run dev:mock -- --port ${port} --strictPort`,
    url: `http://localhost:${port}`,
    reuseExistingServer: false,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
