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

// WCAG 1.4.10 with the list open: an 80-character name with no spaces (the contract's maximum) must wrap,
// not push the page sideways. The mock keeps data in page memory, so the patient is added through the UI
// and the rest of the test navigates without reloading.
test('patient switcher open reflows at 320 px with the longest name', async ({ page }) => {
  const longName = 'Demo' + 'X'.repeat(76)
  await page.setViewportSize({ width: 320, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Add a patient' }).click()
  const form = page.getByRole('form', { name: 'Add a patient' })
  await form.getByLabel('Name').fill(longName)
  await form.getByRole('button', { name: 'Save patient' }).click()
  await expect(page.getByText(`${longName} added.`)).toBeVisible()
  await page.getByRole('link', { name: 'Demo Patient A' }).click()
  await page.getByRole('button', { name: 'Switch patient' }).click()
  await expect(page.getByRole('link', { name: longName })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBe(0)
})
