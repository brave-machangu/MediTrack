import { screen, waitFor, within } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA, TRACE_ID } from '../../mocks/data'
import { server } from '../../mocks/server'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const missedDoses = '/api/v1/patients/:patientId/missed-doses'
const lastWeek = copy.missed.count(4, '20 October', '26 October')

const from = () => screen.getByLabelText(copy.missed.from)
const to = () => screen.getByLabelText(copy.missed.to)
const show = () => screen.getByRole('button', { name: copy.missed.show })
const summary = () => screen.getByRole('group', { name: copy.form.errorSummaryTitle })

/** Renders the page with the default week loaded, recording the query string of every list request. */
async function renderMissed() {
  const queries: string[] = []
  server.use(
    http.get(missedDoses, ({ request }) => {
      queries.push(new URL(request.url).search)
    }),
  )
  const view = renderApp(`/patients/${patientA.id}/missed`)
  await screen.findByText(lastWeek)
  return { ...view, queries }
}

async function choose(user: UserEvent, input: HTMLElement, value: string) {
  await user.clear(input)
  if (value !== '') await user.type(input, value)
}

describe('Missed doses: dates', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("starts on the last 7 days, from the patient's today (DD-7)", async () => {
    await renderMissed()
    expect(from()).toHaveValue('2026-10-20')
    expect(to()).toHaveValue('2026-10-26')
    expect(screen.getByRole('group', { name: copy.missed.range })).toHaveAccessibleDescription(copy.missed.rangeHint)
  })

  it("keeps a date typed before the patient's today arrives, and fills in the other", async () => {
    let release = () => {}
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    // Held back, then passed on to the usual handler.
    server.use(
      http.get('/api/v1/patients/:patientId/doses', async () => {
        await gate
      }),
    )
    const { user } = renderApp(`/patients/${patientA.id}/missed`)
    await user.type(from(), '2026-10-15')

    release()

    await waitFor(() => {
      expect(to()).toHaveValue('2026-10-26')
    })
    expect(from()).toHaveValue('2026-10-15')
  })

  it('shows the chosen dates, asking the server for exactly those', async () => {
    const { user, queries } = await renderMissed()

    await choose(user, from(), '2026-10-15')
    await user.click(show())

    expect(await screen.findByText(copy.missed.count(5, '15 October', '26 October'))).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Thursday 15 October' })).toBeInTheDocument()
    expect(queries.at(-1)).toBe('?from=2026-10-15&to=2026-10-26')
  })

  it('explains a missing date next to its field and in a summary, without asking the server', async () => {
    const { user, queries } = await renderMissed()

    await choose(user, from(), '')
    await user.click(show())

    await waitFor(() => {
      expect(summary()).toHaveFocus()
    })
    expect(from()).toHaveAccessibleDescription(`${copy.form.errorPrefix} ${copy.missed.fromRequired}`)
    await user.click(within(summary()).getByRole('link', { name: copy.missed.fromRequired }))
    expect(from()).toHaveFocus()
    expect(queries).toHaveLength(1)
  })

  it('explains a range that ends before it starts, or covers more than 31 days (AC-23)', async () => {
    const { user, queries } = await renderMissed()
    const group = () => screen.getByRole('group', { name: copy.missed.range })

    await choose(user, from(), '2026-10-27')
    await user.click(show())
    expect(await within(group()).findByText(copy.missed.fromAfterTo)).toBeInTheDocument()

    await choose(user, from(), '2026-09-25')
    await user.click(show())
    expect(await within(group()).findByText(copy.missed.tooLong)).toBeInTheDocument()
    expect(queries).toHaveLength(1)

    // 26 September to 26 October is 31 days with both ends counted: allowed.
    await choose(user, from(), '2026-09-26')
    await user.click(show())
    expect(await screen.findByText(copy.missed.count(5, '26 September', '26 October'))).toBeInTheDocument()
  })

  it("shows the server's reason next to the field when it refuses the dates", async () => {
    const { user } = await renderMissed()
    server.use(
      http.get(missedDoses, () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Invalid request',
            status: 422,
            code: 'VALIDATION_ERROR',
            errors: [{ field: 'to', message: 'The range may cover at most 31 days.' }],
            trace_id: TRACE_ID,
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json', 'X-Trace-Id': TRACE_ID } },
        ),
      ),
    )

    await choose(user, from(), '2026-10-01')
    await user.click(show())

    await waitFor(() => {
      expect(summary()).toHaveFocus()
    })
    expect(to()).toHaveAccessibleDescription(`${copy.form.errorPrefix} The range may cover at most 31 days.`)
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it('regroups when the same dates are shown again, leaving out a dose recorded since (DD-13)', async () => {
    const { user, queries } = await renderMissed()
    const sunday = () => screen.getByRole('list', { name: 'Sunday 25 October' })
    await user.click(show())
    await waitFor(() => {
      expect(queries).toEqual(['', '?from=2026-10-20&to=2026-10-26'])
    })
    await screen.findByRole('list', { name: 'Sunday 25 October' })
    await user.click(within(sunday()).getByRole('button', { name: `${copy.dose.taken}${copy.dose.context('Demo Med Alpha', '14:00')}` }))
    await screen.findByText(copy.missed.count(3, '20 October', '26 October'))
    expect(within(sunday()).getByText(copy.dose.recordedTaken('09:10'))).toBeInTheDocument()

    await user.click(show())

    await waitFor(() => {
      expect(screen.queryByRole('list', { name: 'Sunday 25 October' })).not.toBeInTheDocument()
    })
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })
})
