import { expect, test } from '@playwright/test'

// Demo Patient A and the mock clock from src/mocks/data.ts: 09:10 on Monday 26 October in Africa/Harare.
const todayPath = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01/today'
const mockNow = new Date('2026-10-26T07:10:00Z')
const heading = { level: 1, name: 'Today, Monday 26 October' } as const

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(mockNow)
})

for (const width of [375, 1280]) {
  test(`today with every status at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(todayPath)
    await expect(page.getByRole('heading', heading)).toBeVisible()
    await page.screenshot({ path: `screenshots/out/today-full-${width}.png`, fullPage: true })
  })
}

// Lead review: statuses must stay readable without colour (DESIGN.md §3).
test('today in greyscale', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(todayPath)
  await expect(page.getByRole('heading', heading)).toBeVisible()
  await page.addStyleTag({ content: 'html { filter: grayscale(1); }' })
  await page.screenshot({ path: 'screenshots/out/today-full-375-greyscale.png', fullPage: true })
})

// Page states (DESIGN.md §6.3). `?mock=` picks a scenario from src/mocks/scenarios.ts.
const patientB = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a02/today'
const states = [
  { name: 'loading', path: `${todayPath}?mock=today-loading`, ready: { name: "Loading today's doses…" } },
  { name: 'empty', path: patientB, ready: { name: 'No doses planned for today' } },
  { name: 'error', path: `${todayPath}?mock=today-error`, ready: { name: "Couldn't load today's doses" } },
] as const

for (const width of [375, 1280]) {
  for (const state of states) {
    test(`today ${state.name} at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(state.path)
      await expect(page.getByText(state.ready.name)).toBeVisible()
      await page.screenshot({ path: `screenshots/out/today-${state.name}-${width}.png`, fullPage: true })
    })
  }

  test(`today stale at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`${todayPath}?mock=today-stale`)
    await expect(page.getByRole('heading', heading)).toBeVisible()
    await page.getByRole('button', { name: 'Refresh' }).click()
    await expect(page.getByText("Couldn't refresh. Showing information from 09:10.")).toBeVisible()
    await page.screenshot({ path: `screenshots/out/today-stale-${width}.png`, fullPage: true })
  })
}
