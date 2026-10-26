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

// Medication form (DESIGN.md §4.6): errors next to fields plus a summary, and the saved confirmation.
test('medication form with errors at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  await page.getByRole('button', { name: 'Add a medication' }).click()
  const form = page.getByRole('form', { name: 'Add a medication' })
  await form.getByRole('button', { name: 'Save medication' }).click()
  await expect(form.getByRole('group', { name: 'There is a problem' })).toBeFocused()
  await form.screenshot({ path: 'screenshots/out/medication-form-errors-375.png' })
})

test('medication saved at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  await page.getByRole('button', { name: 'Add a medication' }).click()
  const form = page.getByRole('form', { name: 'Add a medication' })
  await form.getByLabel('Name').fill('Demo Med Zeta')
  await form.getByLabel('Dosage').fill('2 tablets')
  await form.getByRole('button', { name: 'Save medication' }).click()
  await expect(page.getByText('Demo Med Zeta added.')).toBeVisible()
  await page.screenshot({ path: 'screenshots/out/medication-saved-375.png' })
})

// The confirm dialog in a real browser: the native <dialog> traps focus, Esc cancels, focus returns.
test('stop medication dialog at 375 px, and Esc cancels it', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  const stop = page.getByRole('button', { name: 'Stop medication', exact: true }).first()
  await stop.click()
  const dialog = page.getByRole('dialog', { name: 'Stop Demo Med Alpha?' })
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused()
  await page.screenshot({ path: 'screenshots/out/stop-dialog-375.png' })
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(stop).toBeFocused()
})

// Schedule form (DESIGN.md §6.6): field errors, and the overlap message next to the form (AC-34).
const delta = 'Demo Med Delta Extended Release Capsules'

test('schedule form with errors at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  await page.getByRole('article', { name: delta }).getByRole('button', { name: 'Add a schedule' }).click()
  const form = page.getByRole('form', { name: `Add a schedule for ${delta}` })
  await form.getByLabel('Minutes before a dose counts as missed').fill('300')
  await form.getByRole('button', { name: 'Save schedule' }).click()
  await expect(form.getByRole('group', { name: 'There is a problem' })).toBeFocused()
  await form.screenshot({ path: 'screenshots/out/schedule-form-errors-375.png' })
})

test('schedule overlap at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  await page.getByRole('article', { name: delta }).getByRole('button', { name: 'Add a schedule' }).click()
  const form = page.getByRole('form', { name: `Add a schedule for ${delta}` })
  await form.getByLabel('Time 1').fill('09:00')
  await form.getByLabel('Start date').fill('2026-10-28')
  await form.getByRole('button', { name: 'Save schedule' }).click()
  await expect(form.getByRole('alert')).toContainText('already has a schedule on those days')
  await form.screenshot({ path: 'screenshots/out/schedule-overlap-375.png' })
})
