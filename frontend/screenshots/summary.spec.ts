import { expect, test } from '@playwright/test'

// Demo Patients A and B and the mock clock from src/mocks/data.ts.
const pageA = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01/summary'
const pageB = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a02/summary'

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-10-26T07:10:00Z'))
})

const states = [
  { name: 'full', path: pageA, shows: '50.0%' },
  { name: 'empty', path: pageB, shows: 'No doses planned for Monday 26 October.' },
  { name: 'loading', path: `${pageA}?mock=summary-loading`, shows: 'Loading summary…' },
  { name: 'error', path: `${pageA}?mock=summary-error`, shows: "Couldn't load the summary" },
] as const

for (const width of [375, 1280]) {
  for (const state of states) {
    test(`summary ${state.name} at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(state.path)
      await expect(page.getByText(state.shows, { exact: true })).toBeVisible()
      await page.screenshot({ path: `screenshots/out/summary-${state.name}-${width}.png`, fullPage: true })
    })
  }
}

// AC-26: a day with nothing taken, skipped or missed yet.
test('summary with nothing to score at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  await page.getByLabel('Date').fill('2026-10-28')
  await page.getByRole('button', { name: 'Show summary' }).click()
  await expect(page.getByRole('heading', { level: 2, name: 'Wednesday 28 October' })).toBeFocused()
  await expect(page.getByText('No doses to score yet')).toBeVisible()
  await page.screenshot({ path: 'screenshots/out/summary-no-score-375.png', fullPage: true })
})

// WCAG 1.4.10: at 320 CSS px (1280 px at 400% zoom) nothing may need horizontal scrolling.
test('summary reflows at 320 px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.goto(pageA)
  await expect(page.getByText('50.0%', { exact: true })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBe(0)
})
