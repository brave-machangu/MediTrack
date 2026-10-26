import { expect, test } from '@playwright/test'

// Demo Patient A's Medications page; the header's "Switch patient" disclosure (DD-9).
const page375 = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01/medications'

for (const width of [375, 1280]) {
  test(`patient switcher open at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 700 })
    await page.goto(page375)
    await page.getByRole('button', { name: 'Switch patient' }).click()
    await expect(page.getByRole('link', { name: 'Demo Patient B' })).toBeVisible()
    await page.screenshot({ path: `screenshots/out/switcher-open-${width}.png` })
  })
}
