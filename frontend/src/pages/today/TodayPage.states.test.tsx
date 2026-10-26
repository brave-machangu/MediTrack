import { act, screen, waitFor, within } from '@testing-library/react'
import { delay, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { dayA, MOCK_NOW, patientA, patientB, TRACE_ID } from '../../mocks/data'
import { dayOf, json, problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { renderApp } from '../../test/renderApp'
import { namesIn, setClock } from './todayTestHelpers'

const dosesPath = '/api/v1/patients/:patientId/doses'
const todayA = `/patients/${patientA.id}/today`
const { group } = copy.today
const outage = () => problem(503, 'SERVICE_UNAVAILABLE', 'Service unavailable')
const delta = 'Demo Med Delta Extended Release Capsules'

describe('Today page states', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('says the doses are loading in words, not with a spinner', async () => {
    server.use(
      http.get(dosesPath, async () => {
        await delay('infinite')
      }),
    )
    renderApp(todayA)

    expect(await screen.findByText(copy.today.loading)).toHaveAttribute('role', 'status')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(copy.today.titleLoading)
  })

  it('says what is empty and where to go next', async () => {
    renderApp(`/patients/${patientB.id}/today`)

    expect(await screen.findByRole('heading', { level: 2, name: copy.today.empty.title })).toBeInTheDocument()
    expect(screen.getByText(copy.today.empty.body)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: copy.today.empty.action })).toHaveAttribute(
      'href',
      `/patients/${patientB.id}/medications`,
    )
  })

  it('explains a failed load with the support reference, and Retry loads the doses', async () => {
    server.use(http.get(dosesPath, outage, { once: true }))
    const { user } = renderApp(todayA)

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByRole('heading', { name: copy.today.error.title })).toBeInTheDocument()
    expect(alert).toHaveTextContent(copy.error.SERVICE_UNAVAILABLE)
    expect(alert).toHaveTextContent(copy.error.supportReference(TRACE_ID))

    await user.click(within(alert).getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByRole('list', { name: group.attention })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('keeps the doses on screen and says how old they are when a refresh fails', async () => {
    const { user } = renderApp(todayA)
    await screen.findByRole('list', { name: group.attention })

    server.use(http.get(dosesPath, outage))
    await user.click(screen.getByRole('button', { name: copy.today.refresh }))

    expect(await screen.findByText(copy.error.stale('09:10'))).toBeInTheDocument()
    expect(namesIn(group.attention)).toEqual(['Demo Med Gamma', delta])
  })

  it('updates a card in place on a background refresh and regroups only on Refresh (DD-1)', async () => {
    const { user, queryClient } = renderApp(todayA)
    await screen.findByRole('list', { name: group.attention })

    const recordedElsewhere = dayA.map((dose) =>
      dose.medication_name === delta
        ? { ...dose, status: 'taken' as const, dose_log_id: '9c4f2e81-6a3b-4d5c-8e7f-2a1b3c4d5e09', recorded_at: '2026-10-26T07:05:00Z' }
        : dose,
    )
    server.use(http.get(dosesPath, () => json(dayOf(patientA, recordedElsewhere))))

    await act(() => queryClient.refetchQueries())
    // TanStack Query hands the new data to React on a later tick, so wait for what the user would see.
    await waitFor(() => {
      expect(within(screen.getByRole('list', { name: group.attention })).getByText(copy.status.taken)).toBeInTheDocument()
    })
    expect(namesIn(group.attention)).toEqual(['Demo Med Gamma', delta])

    const refresh = screen.getByRole('button', { name: copy.today.refresh })
    await user.click(refresh)

    await waitFor(() => {
      expect(namesIn(group.attention)).toEqual(['Demo Med Gamma'])
    })
    expect(namesIn(group.done)).toContain(delta)
    expect(refresh).toHaveFocus()
    expect(screen.getByText(copy.today.refreshed)).toHaveAttribute('role', 'status')
  })
})
