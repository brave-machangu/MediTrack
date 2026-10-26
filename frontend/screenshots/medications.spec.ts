import { expect, test } from '@playwright/test'

// Demo Patients A and B and the mock clock from src/mocks/data.ts.
const pageA = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01/medications'
const pageB = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a02/medications'

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-10-26T07:10:00Z'))
})

const states = [
  { name: 'full', path: pageA, shows: 'Demo Med Alpha' },
  { name: 'empty', path: pageB, shows: 'No medications yet' },
  { name: 'loading', path: `${pageA}?mock=medications-loading`, shows: 'Loading medications…' },
  { name: 'error', path: `${pageA}?mock=medications-error`, shows: "Couldn't load medications" },
] as const

for (const width of [375, 1280]) {
  for (const state of states) {
    test(`medications ${state.name} at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(state.path)
      await expect(page.getByText(state.shows, { exact: true }).first()).toBeVisible()
      await page.screenshot({ path: `screenshots/out/medications-${state.name}-${width}.png`, fullPage: true })
    })
  }

  test(`medications with stopped ones shown at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(pageA)
    await page.getByRole('checkbox', { name: 'Show stopped medications' }).check()
    await expect(page.getByText('Stopped on 12 October')).toBeVisible()
    await page.screenshot({ path: `screenshots/out/medications-stopped-${width}.png`, fullPage: true })
  })

  test(`medications reflow without sideways scrolling at ${width === 375 ? 320 : width} px`, async ({ page }) => {
    await page.setViewportSize({ width: width === 375 ? 320 : width, height: 900 })
    await page.goto(pageA)
    await expect(page.getByRole('heading', { level: 1, name: 'Medications' })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBe(0)
  })
}
