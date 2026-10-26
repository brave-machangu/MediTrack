import { screen, within } from '@testing-library/react'
import { http } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PlannedDose } from '../../api/doses'
import { copy } from '../../copy'
import { dayA, MOCK_NOW, patientA, patientB } from '../../mocks/data'
import { dayOf, json } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'
import { cardIn, namesIn, setClock } from './todayTestHelpers'

const { group } = copy.today

async function renderToday(patientId = patientA.id) {
  renderApp(`/patients/${patientId}/today`)
  await screen.findByRole('heading', { level: 1, name: /^Today, / })
}

function serveDay(patient: typeof patientA, doses: PlannedDose[]) {
  server.use(http.get('/api/v1/patients/:patientId/doses', () => json(dayOf(patient, doses))))
}

describe('Today page', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it("shows the patient's local today grouped as in the design brief", async () => {
    setClock(MOCK_NOW)
    await renderToday()

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Today, Monday 26 October')
    expect(namesIn(group.attention)).toEqual(['Demo Med Gamma', 'Demo Med Delta Extended Release Capsules'])
    expect(namesIn(group.later)).toEqual(['Demo Med Alpha', 'Demo Med Beta'])
    expect(namesIn(group.done)).toEqual(['Demo Med Alpha', 'Demo Med Beta', 'Demo Med Gamma'])
    expect(screen.queryByRole('list', { name: group.missed })).not.toBeInTheDocument()
  })

  it.each([
    [group.attention, 0, copy.status.missed],
    [group.attention, 1, copy.status.due],
    [group.later, 0, copy.status.upcoming],
    [group.done, 0, copy.status.takenLate],
    [group.done, 1, copy.status.taken],
    [group.done, 2, copy.status.skipped],
  ])('shows status as text with an icon: %s card %i is "%s" (AC-28)', async (groupName, index, label) => {
    setClock(MOCK_NOW)
    await renderToday()

    const badge = within(cardIn(groupName, index)).getByText(label)
    expect(badge.querySelector('svg[aria-hidden="true"]')).not.toBeNull()
  })

  it('summarises progress and names the next dose', async () => {
    setClock(MOCK_NOW)
    await renderToday()

    expect(screen.getByText(copy.today.progress(3, 7))).toBeInTheDocument()
    expect(screen.getByText(copy.today.next('14:00', 'Demo Med Alpha'))).toBeInTheDocument()
  })

  it('says when upcoming doses can be recorded and when doses were recorded, in patient time', async () => {
    setClock(MOCK_NOW)
    await renderToday()

    expect(within(cardIn(group.later, 0)).getByText(copy.dose.recordFrom('13:00'))).toBeInTheDocument()
    expect(within(cardIn(group.done, 0)).getByText(copy.dose.recordedTaken('08:20'))).toBeInTheDocument()
    expect(within(cardIn(group.done, 2)).getByText(copy.dose.recordedSkipped('08:50'))).toBeInTheDocument()
    expect(within(cardIn(group.attention, 0)).getByText(copy.dose.noRecord)).toBeInTheDocument()
  })

  it("notes the patient's timezone only when it differs from the browser's", async () => {
    setClock(MOCK_NOW)
    await renderToday()
    expect(screen.getByText(copy.today.timezoneNote('Africa/Harare'))).toBeInTheDocument()
  })

  it('leaves the timezone note out when the browser is in the same timezone', async () => {
    setClock(MOCK_NOW)
    serveDay({ ...patientA, timezone: 'Asia/Tokyo' }, dayA)
    await renderToday()
    expect(screen.queryByText(/^Times shown in/)).not.toBeInTheDocument()
  })

  it('shows New York dates and times for a New York patient while the machine is in Tokyo (AC-35)', async () => {
    setClock('2026-10-26T13:00:00Z')
    const template = dayA.find((dose) => dose.status === 'taken' && !dose.late)
    if (template === undefined) throw new Error('mock day has no on-time taken dose')
    serveDay(patientB, [
      { ...template, local_time: '08:00', scheduled_for: '2026-10-26T12:00:00Z', recorded_at: '2026-10-26T12:05:00Z' },
    ])
    await renderToday(patientB.id)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Today, Monday 26 October')
    expect(screen.getByText(copy.today.timezoneNote('America/New York'))).toBeInTheDocument()
    const card = cardIn(group.done, 0)
    expect(within(card).getByText('08:00')).toBeInTheDocument()
    expect(within(card).getByText(copy.dose.recordedTaken('08:05'))).toBeInTheDocument()
  })

  it('moves a missed dose under Missed once it can no longer be recorded', async () => {
    setClock('2026-10-27T05:00:00Z')
    await renderToday()

    expect(namesIn(group.missed)).toEqual(['Demo Med Gamma'])
    expect(within(cardIn(group.missed, 0)).getByText(copy.dose.windowClosed)).toBeInTheDocument()
    expect(namesIn(group.attention)).toEqual(['Demo Med Delta Extended Release Capsules'])
  })

  it('has no serious or critical axe violations (AC-28)', async () => {
    setClock(MOCK_NOW)
    await renderToday()
    expect(await seriousAxeViolations()).toEqual([])
  })
})
