import { screen, waitFor, within } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA, patientB, TRACE_ID } from '../../mocks/data'
import { problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const dailySummary = '/api/v1/patients/:patientId/adherence/daily'
const outage = () => problem(503, 'SERVICE_UNAVAILABLE', 'Service unavailable')

const dateField = () => screen.getByLabelText(copy.summary.date)
const show = () => screen.getByRole('button', { name: copy.summary.show })
const summaryBox = () => screen.getByRole('group', { name: copy.form.errorSummaryTitle })
/** The counts table's rows as "label value", in order. */
const rows = () =>
  within(screen.getByRole('table'))
    .getAllByRole('row')
    .map((row) => row.textContent)

/** Renders the page for a patient, recording the query string of every summary request. */
async function renderSummary(patientId = patientA.id) {
  const queries: string[] = []
  server.use(
    http.get(dailySummary, ({ request }) => {
      queries.push(new URL(request.url).search)
    }),
  )
  const view = renderApp(`/patients/${patientId}/summary`)
  await screen.findByRole('heading', { level: 2 })
  return { ...view, queries }
}

async function choose(user: UserEvent, value: string) {
  await user.clear(dateField())
  if (value !== '') await user.type(dateField(), value)
  await user.click(show())
}

describe('Daily summary page', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("shows today's counts and adherence exactly as the server returns them (FR-09)", async () => {
    const { queries } = await renderSummary()

    expect(screen.getByRole('heading', { level: 2, name: 'Monday 26 October' })).toBeInTheDocument()
    expect(screen.getByText(copy.summary.percent('50.0'))).toBeInTheDocument()
    expect(screen.getByText(copy.summary.adherenceExplain)).toBeInTheDocument()
    expect(screen.getByRole('table', { name: copy.summary.tableCaption('Monday 26 October') })).toBeInTheDocument()
    expect(rows()).toEqual([
      `${copy.summary.planned}7`,
      `${copy.summary.taken}2`,
      `${copy.summary.takenLate}1`,
      `${copy.summary.skipped}1`,
      `${copy.summary.missed}1`,
      `${copy.summary.pending}3`,
    ])
    // No date is sent, so the server's patient-local today decides it.
    expect(queries).toEqual([''])
    expect(dateField()).toHaveValue('2026-10-26')
  })

  it("keeps a date typed before the patient's today arrives", async () => {
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
    const { user } = renderApp(`/patients/${patientA.id}/summary`)
    await user.type(dateField(), '2026-10-25')

    release()

    await screen.findByRole('heading', { level: 2, name: 'Monday 26 October' })
    expect(dateField()).toHaveValue('2026-10-25')
  })

  it('shows the chosen date, asking the server for exactly that one, and moves focus to it', async () => {
    const { user, queries } = await renderSummary()

    await choose(user, '2026-10-25')

    const heading = await screen.findByRole('heading', { level: 2, name: 'Sunday 25 October' })
    await waitFor(() => {
      expect(heading).toHaveFocus()
    })
    expect(screen.getByText(copy.summary.percent('80.0'))).toBeInTheDocument()
    expect(queries.at(-1)).toBe('?date=2026-10-25')
  })

  it('says "No doses to score yet" when nothing has been taken, skipped or missed (AC-26)', async () => {
    const { user } = await renderSummary()

    await choose(user, '2026-10-28')

    expect(await screen.findByText(copy.summary.noScore)).toBeInTheDocument()
    expect(screen.getByText(copy.summary.noScoreExplain)).toBeInTheDocument()
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument()
    expect(rows()).toContain(`${copy.summary.pending}7`)
  })

  it('says when no doses are planned, without a table', async () => {
    await renderSummary(patientB.id)
    expect(screen.getByText(copy.summary.empty('Monday 26 October'))).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('explains a missing date next to the field and in a summary, without asking the server', async () => {
    const { user, queries } = await renderSummary()

    await choose(user, '')

    await waitFor(() => {
      expect(summaryBox()).toHaveFocus()
    })
    expect(dateField()).toHaveAccessibleDescription(`${copy.form.errorPrefix} ${copy.summary.dateRequired}`)
    expect(queries).toHaveLength(1)
  })

  it("shows the server's reason next to the date when it refuses it", async () => {
    const { user } = await renderSummary()
    server.use(
      http.get(dailySummary, () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Invalid request',
            status: 422,
            code: 'VALIDATION_ERROR',
            errors: [{ field: 'date', message: 'Use a date like 2026-10-26.' }],
            trace_id: TRACE_ID,
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json', 'X-Trace-Id': TRACE_ID } },
        ),
      ),
    )

    await choose(user, '2026-10-24')

    await waitFor(() => {
      expect(summaryBox()).toHaveFocus()
    })
    expect(dateField()).toHaveAccessibleDescription(`${copy.form.errorPrefix} Use a date like 2026-10-26.`)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('explains a failed load with the support reference, and Retry loads the summary', async () => {
    server.use(http.get(dailySummary, outage, { once: true }))
    const { user } = renderApp(`/patients/${patientA.id}/summary`)

    expect(await screen.findByRole('heading', { name: copy.summary.error.title })).toBeInTheDocument()
    expect(screen.getByText(copy.error.supportReference(TRACE_ID))).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByText(copy.summary.percent('50.0'))).toBeInTheDocument()
  })

  it('keeps the summary when a refresh fails, with Retry in the notice', async () => {
    const { user } = await renderSummary()
    await choose(user, '2026-10-26')
    await screen.findByRole('heading', { level: 2, name: 'Monday 26 October' })
    server.use(http.get(dailySummary, outage, { once: true }))

    // The same date again refreshes it, and that refresh fails.
    await user.click(show())

    expect(await screen.findByText(copy.error.stale('09:10'))).toBeInTheDocument()
    expect(screen.getByText(copy.summary.percent('50.0'))).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: copy.action.retry }))
    await waitFor(() => {
      expect(screen.queryByText(copy.error.stale('09:10'))).not.toBeInTheDocument()
    })
  })

  it('has no serious or critical axe violations', async () => {
    await renderSummary()
    expect(await seriousAxeViolations()).toEqual([])
  })
})
