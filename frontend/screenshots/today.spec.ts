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

// Dose cards (DESIGN.md §6.4). Element screenshots keep the files small.
const delta = { name: 'Demo Med Delta Extended Release Capsules' }
const cardStates = [
  { name: 'saving', query: '?mock=record-slow', shows: 'Saving…' },
  { name: 'not-recorded', query: '?mock=record-error', shows: 'Not recorded. Something went wrong. Please try again.' },
  { name: 'recorded', query: '', shows: 'Taken at 09:10' },
] as const

for (const state of cardStates) {
  test(`dose card ${state.name} at 375 px`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 900 })
    await page.goto(`${todayPath}${state.query}`)
    const card = page.getByRole('article', delta)
    await card.getByRole('button', { name: /^Taken/ }).click()
    await expect(card.getByText(state.shows)).toBeVisible()
    await card.screenshot({ path: `screenshots/out/card-${state.name}-375.png` })
  })
}

test('dose card once Undo is no longer possible (DD-2)', async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-10-27T05:40:00Z'))
  await page.setViewportSize({ width: 375, height: 900 })
  await page.goto(todayPath)
  const card = page.getByRole('listitem').filter({ hasText: 'Taken at 08:20' })
  await expect(card.getByText("Undo is no longer available because this dose can't be recorded again.")).toBeVisible()
  await card.screenshot({ path: 'screenshots/out/card-undo-closed-375.png' })
})

// AC-28 / DESIGN.md §2.3: Taken and Skipped are at least 48 px tall and at least 8 px apart.
for (const width of [375, 1280]) {
  test(`dose buttons are big enough and far enough apart at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(todayPath)
    const card = page.getByRole('article', delta)
    const taken = await card.getByRole('button', { name: /^Taken/ }).boundingBox()
    const skipped = await card.getByRole('button', { name: /^Skipped/ }).boundingBox()
    if (taken === null || skipped === null) throw new Error('dose buttons are not on screen')
    expect(taken.height).toBeGreaterThanOrEqual(48)
    expect(skipped.height).toBeGreaterThanOrEqual(48)
    const gap = width < 600 ? skipped.y - (taken.y + taken.height) : skipped.x - (taken.x + taken.width)
    expect(gap).toBeGreaterThanOrEqual(8)
  })
}
