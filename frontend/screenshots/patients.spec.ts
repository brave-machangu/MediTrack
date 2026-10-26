import { expect, test } from '@playwright/test'

const states = [
  { name: 'full', path: '/', shows: 'Demo Patient A' },
  { name: 'loading', path: '/?mock=patients-loading', shows: 'Loading patients…' },
  { name: 'error', path: '/?mock=patients-error', shows: "Couldn't load patients" },
] as const

for (const width of [375, 1280]) {
  for (const state of states) {
    test(`patients ${state.name} at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(state.path)
      await expect(page.getByText(state.shows, { exact: true }).first()).toBeVisible()
      await page.screenshot({ path: `screenshots/out/patients-${state.name}-${width}.png`, fullPage: true })
    })
  }
}

test('patient form with errors at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Add a patient' }).click()
  const form = page.getByRole('form', { name: 'Add a patient' })
  await form.getByRole('button', { name: 'Save patient' }).click()
  await expect(form.getByRole('group', { name: 'There is a problem' })).toBeFocused()
  await form.screenshot({ path: 'screenshots/out/patient-form-errors-375.png' })
})

test('timezone locked once doses are recorded, at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Edit', exact: true }).first().click()
  const form = page.getByRole('form', { name: 'Edit Demo Patient A' })
  await form.getByLabel('Timezone').selectOption('Europe/London')
  await form.getByRole('button', { name: 'Save patient' }).click()
  await expect(form.getByText("The timezone can't be changed after doses have been recorded.").first()).toBeVisible()
  await form.screenshot({ path: 'screenshots/out/patient-timezone-locked-375.png' })
})

test('patients reflow without sideways scrolling at 320 px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1, name: 'Patients' })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBe(0)
})

// WCAG 1.4.10 with the longest name the contract allows (80 characters, no spaces): it wraps in the list,
// the saved message and the form heading instead of pushing the page sideways.
test('patients reflow at 320 px with the longest name, its form open', async ({ page }) => {
  const longName = 'Demo' + 'X'.repeat(76)
  await page.setViewportSize({ width: 320, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Add a patient' }).click()
  const addForm = page.getByRole('form', { name: 'Add a patient' })
  await addForm.getByLabel('Name').fill(longName)
  await addForm.getByRole('button', { name: 'Save patient' }).click()
  await expect(page.getByText(`${longName} added.`)).toBeVisible()
  await page.getByRole('button', { name: 'Edit', exact: true }).last().click()
  await expect(page.getByRole('heading', { name: `Edit ${longName}` })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBe(0)
})
