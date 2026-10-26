import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { dayA, MOCK_NOW, patientA, TRACE_ID } from '../../mocks/data'
import { problem, recordMockDose } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { renderApp } from '../../test/renderApp'
import { cardIn, namesIn, setClock } from './todayTestHelpers'

const doseLogs = '/api/v1/dose-logs'
const { group } = copy.today
const deltaName = 'Demo Med Delta Extended Release Capsules'
const recordedNow = copy.dose.recordedTaken('09:10')

// Accessible names carry the dose, e.g. "Taken, Demo Med Delta Extended Release Capsules at 08:30".
const named = (label: string, medication: string, time: string) => `${label}${copy.dose.context(medication, time)}`

const deltaCard = () => screen.getByRole('article', { name: deltaName })
const deltaTaken = () => within(deltaCard()).getByRole('button', { name: named(copy.dose.taken, deltaName, '08:30') })

function deltaDose() {
  const dose = dayA.find((planned) => planned.medication_name === deltaName)
  if (dose === undefined) throw new Error('mock day has no Delta dose')
  return dose
}

async function renderToday() {
  const view = renderApp(`/patients/${patientA.id}/today`)
  await screen.findByRole('list', { name: group.attention })
  return view
}

describe('Today page: recording and undo', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('records a due dose as taken, shows what the server confirmed, and keeps the card in place (AC-14)', async () => {
    const { user } = await renderToday()

    await user.click(deltaTaken())

    const result = await within(deltaCard()).findByText(recordedNow)
    expect(within(deltaCard()).getByText(copy.status.taken)).toBeInTheDocument()
    await waitFor(() => {
      expect(result).toHaveFocus()
    })
    expect(namesIn(group.attention)).toContain(deltaName)
  })

  it('sends one request for a double tap and disables both buttons while saving (AC-21)', async () => {
    let posts = 0
    let release = () => {}
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    server.use(
      http.post(doseLogs, async () => {
        posts += 1
        await gate
      }),
    )
    const { user } = await renderToday()

    await user.dblClick(deltaTaken())

    const card = deltaCard()
    expect(within(card).getByRole('button', { name: named(copy.action.saving, deltaName, '08:30') })).toBeDisabled()
    expect(within(card).getByRole('button', { name: named(copy.dose.skipped, deltaName, '08:30') })).toBeDisabled()
    release()
    await within(card).findByText(recordedNow)
    expect(posts).toBe(1)
  })

  it('treats 409 as "Already recorded" and shows the server record, not an error (AC-21)', async () => {
    const { user } = await renderToday()
    recordMockDose({ ...deltaDose(), status: 'taken' }) // another device got there first

    await user.click(deltaTaken())

    expect(await within(deltaCard()).findByText(copy.error.DUPLICATE_DOSE_LOG)).toBeInTheDocument()
    expect(within(deltaCard()).getByText(recordedNow)).toBeInTheDocument()
    expect(within(deltaCard()).queryByRole('alert')).not.toBeInTheDocument()
  })

  it('never shows a dose as taken after a server error; offers Retry and the support reference (AC-36)', async () => {
    server.use(http.post(doseLogs, () => problem(500, 'INTERNAL_ERROR', 'Boom'), { once: true }))
    const { user } = await renderToday()

    await user.click(deltaTaken())

    const message = await within(deltaCard()).findByText(`${copy.dose.notRecorded} ${copy.error.INTERNAL_ERROR}`)
    expect(within(deltaCard()).getByText(copy.error.supportReference(TRACE_ID))).toBeInTheDocument()
    expect(within(deltaCard()).getByText(copy.status.due)).toBeInTheDocument()
    expect(within(deltaCard()).queryByText(copy.status.taken)).not.toBeInTheDocument()
    await waitFor(() => {
      expect(message).toHaveFocus()
    })

    await user.click(within(deltaCard()).getByRole('button', { name: named(copy.action.retry, deltaName, '08:30') }))
    expect(await within(deltaCard()).findByText(recordedNow)).toBeInTheDocument()
  })

  it('shows the dose as recorded when a retry gets 409, because the first attempt was saved (AC-36)', async () => {
    server.use(http.post(doseLogs, () => problem(503, 'SERVICE_UNAVAILABLE', 'Down'), { once: true }))
    const { user } = await renderToday()
    await user.click(deltaTaken())
    await within(deltaCard()).findByText(`${copy.dose.notRecorded} ${copy.error.SERVICE_UNAVAILABLE}`)

    recordMockDose({ ...deltaDose(), status: 'taken' }) // the server did store the first attempt after all
    await user.click(within(deltaCard()).getByRole('button', { name: named(copy.action.retry, deltaName, '08:30') }))

    expect(await within(deltaCard()).findByText(copy.error.DUPLICATE_DOSE_LOG)).toBeInTheDocument()
    expect(within(deltaCard()).getByText(recordedNow)).toBeInTheDocument()
    expect(within(deltaCard()).queryByRole('alert')).not.toBeInTheDocument()
  })

  it('explains a network failure without a support reference', async () => {
    server.use(http.post(doseLogs, () => HttpResponse.error(), { once: true }))
    const { user } = await renderToday()

    await user.click(deltaTaken())

    expect(await within(deltaCard()).findByText(`${copy.dose.notRecorded} ${copy.error.network}`)).toBeInTheDocument()
    expect(within(deltaCard()).queryByText(/^Support reference/)).not.toBeInTheDocument()
  })

  it('explains a rejected record without offering Retry', async () => {
    server.use(http.post(doseLogs, () => problem(422, 'OUTSIDE_LOG_WINDOW', 'Outside'), { once: true }))
    const { user } = await renderToday()

    await user.click(deltaTaken())

    expect(await within(deltaCard()).findByText(copy.error.OUTSIDE_LOG_WINDOW)).toBeInTheDocument()
    expect(within(deltaCard()).queryByRole('button', { name: /^Retry/ })).not.toBeInTheDocument()
    expect(deltaTaken()).toBeEnabled()
  })

  it('undoes a record, returns the dose to its time-based status, and lets it be recorded again (AC-20)', async () => {
    const { user } = await renderToday()
    const beta = cardIn(group.done, 1)

    await user.click(within(beta).getByRole('button', { name: named(copy.dose.undo, 'Demo Med Beta', '07:30') }))

    expect(await within(beta).findByText(copy.status.missed)).toBeInTheDocument()
    expect(within(beta).getByText(copy.dose.undone)).toHaveAttribute('role', 'status')
    expect(within(beta).getByRole('heading', { level: 3 })).toHaveFocus()

    await user.click(within(beta).getByRole('button', { name: named(copy.dose.taken, 'Demo Med Beta', '07:30') }))
    expect(await within(beta).findByText(copy.status.takenLate)).toBeInTheDocument()
  })

  it('offers no Undo once a dose can no longer be recorded, and says why (DD-2)', async () => {
    setClock('2026-10-27T05:40:00Z')
    await renderToday()

    const alpha = cardIn(group.done, 0)
    expect(within(alpha).queryByRole('button', { name: /^Undo/ })).not.toBeInTheDocument()
    expect(within(alpha).getByText(copy.dose.undoClosed)).toBeInTheDocument()
    expect(within(cardIn(group.done, 2)).getByRole('button', { name: /^Undo/ })).toBeInTheDocument()
  })

  it('records and undoes with the keyboard alone (AC-28)', async () => {
    const { user } = await renderToday()

    for (let presses = 0; presses < 20 && document.activeElement !== deltaTaken(); presses += 1) {
      await user.tab()
    }
    expect(deltaTaken()).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(await within(deltaCard()).findByText(recordedNow)).toBeInTheDocument()

    await user.tab()
    expect(within(deltaCard()).getByRole('button', { name: /^Undo/ })).toHaveFocus()
    await user.keyboard(' ')
    await waitFor(() => {
      expect(within(deltaCard()).getByRole('heading', { level: 3 })).toHaveFocus()
    })
    expect(deltaTaken()).toBeEnabled()
  })
})
