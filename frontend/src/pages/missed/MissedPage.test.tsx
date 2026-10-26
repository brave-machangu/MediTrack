import { screen, waitFor, within } from '@testing-library/react'
import { http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA, patientB, TRACE_ID } from '../../mocks/data'
import { problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const missedDoses = '/api/v1/patients/:patientId/missed-doses'
const todayDoses = '/api/v1/patients/:patientId/doses'
const outage = () => problem(503, 'SERVICE_UNAVAILABLE', 'Service unavailable')
const lastWeek = copy.missed.count(4, '20 October', '26 October')
const afterRecording = copy.missed.count(3, '20 October', '26 October')

// Accessible names carry the dose, e.g. "Taken, Demo Med Alpha at 14:00".
const named = (label: string, medication: string, time: string) => `${label}${copy.dose.context(medication, time)}`

/** The card for a medication under one date heading. */
const card = (date: string, medication: string) =>
  within(screen.getByRole('list', { name: date })).getByRole('article', { name: medication })
const alphaSunday = () => card('Sunday 25 October', 'Demo Med Alpha')
const alphaButton = (label: string) => within(alphaSunday()).getByRole('button', { name: named(label, 'Demo Med Alpha', '14:00') })

async function renderMissed(patientId = patientA.id) {
  const view = renderApp(`/patients/${patientId}/missed`)
  await screen.findByRole('heading', { level: 1, name: copy.missed.title })
  return view
}

describe('Missed doses page', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the last 7 days, newest first, under a heading per date (AC-22)', async () => {
    const queries: string[] = []
    server.use(
      http.get(missedDoses, ({ request }) => {
        queries.push(new URL(request.url).search)
      }),
    )
    await renderMissed()

    expect(await screen.findByText(lastWeek)).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)).toEqual([
      'Monday 26 October',
      'Sunday 25 October',
      'Thursday 22 October',
      'Tuesday 20 October',
    ])
    // No range is sent, so the server's patient-local today decides it, not the browser's.
    expect(queries).toEqual([''])
  })

  it("says only that no dose was recorded, plus the disclaimer's last sentence (AC-38, DD-4)", async () => {
    await renderMissed()
    await screen.findByText(lastWeek)

    expect(screen.getByText(copy.app.disclaimerInset)).toBeInTheDocument()
    for (const article of screen.getAllByRole('article')) {
      expect(within(article).getByText(copy.dose.noRecord)).toBeInTheDocument()
    }
    const gamma = card('Monday 26 October', 'Demo Med Gamma')
    expect(within(gamma).getByText(copy.dose.recordUntil('06:00', 'Tuesday 27 October'))).toBeInTheDocument()
    expect(within(gamma).getByRole('button', { name: named(copy.dose.taken, 'Demo Med Gamma', '06:00') })).toBeEnabled()
    const beta = card('Thursday 22 October', 'Demo Med Beta')
    expect(within(beta).getByText(copy.dose.windowClosed)).toBeInTheDocument()
    expect(within(beta).queryByRole('button')).not.toBeInTheDocument()
  })

  it('records a missed dose late and keeps its card after the list leaves it out (AC-24, DD-13)', async () => {
    const { user } = await renderMissed()
    await screen.findByText(lastWeek)

    await user.click(alphaButton(copy.dose.taken))

    expect(await screen.findByText(afterRecording)).toBeInTheDocument()
    const result = within(alphaSunday()).getByText(copy.dose.recordedTaken('09:10'))
    expect(within(alphaSunday()).getByText(copy.status.takenLate)).toBeInTheDocument()
    await waitFor(() => {
      expect(result).toHaveFocus()
    })
    expect(alphaButton(copy.dose.undo)).toBeEnabled()
  })

  it('puts the dose back as missed after Undo, in the same place', async () => {
    const { user } = await renderMissed()
    await screen.findByText(lastWeek)
    await user.click(alphaButton(copy.dose.taken))
    await screen.findByText(afterRecording)

    await user.click(alphaButton(copy.dose.undo))

    expect(await screen.findByText(lastWeek)).toBeInTheDocument()
    await waitFor(() => {
      expect(within(alphaSunday()).getByRole('heading', { level: 3 })).toHaveFocus()
    })
    expect(within(alphaSunday()).getByText(copy.dose.noRecord)).toBeInTheDocument()
    expect(alphaButton(copy.dose.taken)).toBeEnabled()
    expect(screen.getByText(copy.dose.undone)).toBeInTheDocument()
  })

  it('says when there are no missed doses', async () => {
    await renderMissed(patientB.id)
    expect(await screen.findByText(copy.missed.empty('20 October', '26 October'))).toBeInTheDocument()
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it("counts in the last 7 days when the patient's today isn't known (DD-7)", async () => {
    server.use(http.get(todayDoses, outage))
    await renderMissed()
    expect(await screen.findByText(copy.missed.countDefault(4))).toBeInTheDocument()
  })

  it('explains a failed load with the support reference, and Retry loads the list', async () => {
    server.use(http.get(missedDoses, outage, { once: true }))
    const { user } = await renderMissed()

    expect(await screen.findByRole('heading', { name: copy.missed.error.title })).toBeInTheDocument()
    expect(screen.getByText(copy.error.supportReference(TRACE_ID))).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByText(lastWeek)).toBeInTheDocument()
  })

  it('keeps the list when a refresh fails, with Retry in the notice', async () => {
    const { user } = await renderMissed()
    await screen.findByText(lastWeek)
    server.use(http.get(missedDoses, outage, { once: true }))

    // Recording refreshes the list, and that refresh fails.
    await user.click(alphaButton(copy.dose.taken))

    expect(await screen.findByText(copy.error.stale('09:10'))).toBeInTheDocument()
    expect(screen.getByText(lastWeek)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByText(afterRecording)).toBeInTheDocument()
    expect(screen.queryByText(copy.error.stale('09:10'))).not.toBeInTheDocument()
  })

  it('has no serious or critical axe violations', async () => {
    await renderMissed()
    await screen.findByText(lastWeek)
    expect(await seriousAxeViolations()).toEqual([])
  })
})
