import { expect, test } from '@playwright/test'

// Demo Patient A from src/mocks/data.ts
const patientId = '6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01'

// `ready` is text that shows once the screen's data has loaded; the h1 can come first.
const screens = [
  { name: 'patients', path: '/', ready: 'Demo Patient A' },
  { name: 'today', path: `/patients/${patientId}/today`, ready: 'Needs attention' },
  { name: 'patient-not-found', path: '/patients/00000000-0000-4000-8000-000000000000/today', ready: null },
  { name: 'page-not-found', path: '/no-such-page', ready: null },
]

for (const width of [375, 1280]) {
  for (const screen of screens) {
    test(`${screen.name} at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(screen.path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      if (screen.ready !== null) await expect(page.getByText(screen.ready, { exact: true })).toBeVisible()
      await page.screenshot({ path: `screenshots/out/${screen.name}-${width}.png`, fullPage: true })
    })
  }
}

// WCAG 1.4.10: at 320 CSS px (1280 px at 400% zoom) nothing may need horizontal scrolling.
for (const screen of screens) {
  test(`${screen.name} reflows at 320 px`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 900 })
    await page.goto(screen.path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBe(0)
  })
}
