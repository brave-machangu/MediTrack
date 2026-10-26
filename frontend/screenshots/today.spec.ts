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
