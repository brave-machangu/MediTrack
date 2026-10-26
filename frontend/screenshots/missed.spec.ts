import { expect, test } from '@playwright/test'

// Demo Patients A and B and the mock clock from src/mocks/data.ts.
const pageA = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01/missed'
const pageB = '/patients/6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a02/missed'

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-10-26T07:10:00Z'))
})

const states = [
  { name: 'full', path: pageA, shows: '4 missed doses from 20 October to 26 October.' },
  { name: 'empty', path: pageB, shows: 'No missed doses from 20 October to 26 October.' },
  { name: 'loading', path: `${pageA}?mock=missed-loading`, shows: 'Loading missed doses…' },
  { name: 'error', path: `${pageA}?mock=missed-error`, shows: "Couldn't load missed doses" },
] as const

for (const width of [375, 1280]) {
  for (const state of states) {
    test(`missed ${state.name} at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(state.path)
      await expect(page.getByText(state.shows, { exact: true })).toBeVisible()
      await page.screenshot({ path: `screenshots/out/missed-${state.name}-${width}.png`, fullPage: true })
    })
  }
}

// DD-13: the card stays where it was, with the record and Undo, after the server's list leaves it out.
test('missed dose recorded late at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  const sunday = page.getByRole('list', { name: 'Sunday 25 October' })
  await sunday.getByRole('button', { name: /^Taken/ }).click()
  await expect(page.getByText('3 missed doses from 20 October to 26 October.')).toBeVisible()
  await expect(sunday.getByText('Taken at 09:10')).toBeFocused()
  await sunday.getByRole('article').screenshot({ path: 'screenshots/out/missed-recorded-375.png' })
})

// Dates (DESIGN.md §4.6): errors next to the fields plus a summary, before anything is sent.
test('missed dates with errors at 375 px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(pageA)
  await page.getByLabel('From').fill('2026-09-01')
  await page.getByRole('button', { name: 'Show missed doses' }).click()
  await expect(page.getByRole('group', { name: 'There is a problem' })).toBeFocused()
  await page.locator('form').screenshot({ path: 'screenshots/out/missed-dates-errors-375.png' })
})

// WCAG 1.4.10: at 320 CSS px (1280 px at 400% zoom) nothing may need horizontal scrolling.
test('missed doses reflow at 320 px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.goto(pageA)
  await expect(page.getByText('4 missed doses from 20 October to 26 October.')).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBe(0)
})
