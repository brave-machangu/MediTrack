import { screen, within } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import { http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA, TRACE_ID } from '../../mocks/data'
import { problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const alpha = () => screen.getByRole('article', { name: 'Demo Med Alpha' })

async function renderMedications() {
  const view = renderApp(`/patients/${patientA.id}/medications`)
  await screen.findByRole('article', { name: 'Demo Med Alpha' })
  return view
}

async function open(user: UserEvent, label: string, formName: string) {
  await user.click(within(alpha()).getByRole('button', { name: label, description: '07:00 and 14:00' }))
  return screen.getByRole('form', { name: formName })
}

async function replace(user: UserEvent, input: HTMLElement, value: string) {
  await user.clear(input)
  await user.type(input, value)
}

describe('Schedules with recorded doses', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('explains that only the end date can change, and offers Change schedule and Change end date', async () => {
    await renderMedications()
    const card = within(alpha())
    expect(card.getByText(copy.schedule.hasLogs)).toBeInTheDocument()
    expect(card.getByRole('button', { name: copy.schedule.change, description: '07:00 and 14:00' })).toBeInTheDocument()
    expect(card.getByRole('button', { name: copy.schedule.changeEnd, description: '07:00 and 14:00' })).toBeInTheDocument()
  })

  it('changes the end date (AC-06)', async () => {
    const { user } = await renderMedications()
    const form = await open(user, copy.schedule.changeEnd, copy.endDate.title)
    const end = within(form).getByLabelText(copy.endDate.label)
    expect(end).toHaveValue('2026-10-26')

    await replace(user, end, '2026-11-30')
    await user.click(within(form).getByRole('button', { name: copy.changeSchedule.save }))

    expect(await screen.findByText(copy.endDate.saved)).toBeInTheDocument()
    expect(within(alpha()).getByText(copy.schedule.fromTo('1 October', '30 November'))).toBeInTheDocument()
  })

  it('shows the reason next to the field when the server refuses an end date (AC-06)', async () => {
    const { user } = await renderMedications()
    const form = await open(user, copy.schedule.changeEnd, copy.endDate.title)
    await replace(user, within(form).getByLabelText(copy.endDate.label), '2026-10-20')
    await user.click(within(form).getByRole('button', { name: copy.changeSchedule.save }))

    const message = 'End date must be on or after today and the last recorded dose.'
    expect(await within(form).findByRole('link', { name: message })).toBeInTheDocument()
    expect(within(form).getByLabelText(copy.endDate.label)).toHaveAttribute('aria-invalid', 'true')
  })

  it('ends the schedule today and starts the new one tomorrow by default (AC-34, requirements §4.4)', async () => {
    const { user } = await renderMedications()
    const form = await open(user, copy.schedule.change, copy.changeSchedule.title)
    expect(within(form).getByLabelText(copy.changeSchedule.endsOn)).toHaveValue('2026-10-26')
    expect(within(form).getByLabelText(copy.changeSchedule.startsOnLabel)).toHaveValue('2026-10-27')
    expect(within(form).getByText(copy.changeSchedule.startsTomorrow)).toBeInTheDocument()
    expect(within(form).getByLabelText(copy.scheduleForm.time(1))).toHaveValue('07:00')

    await replace(user, within(form).getByLabelText(copy.scheduleForm.time(1)), '08:00')
    await user.click(within(form).getByRole('button', { name: copy.changeSchedule.save }))

    expect(await screen.findByText(copy.changeSchedule.done('27 October'))).toBeInTheDocument()
    const card = within(alpha())
    expect(card.getByText(copy.schedule.fromTo('1 October', '26 October'))).toBeInTheDocument()
    expect(card.getByText('08:00 and 14:00')).toBeInTheDocument()
    expect(card.getByText(copy.schedule.from('27 October'))).toBeInTheDocument()
  })

  it('moves the new start with the end date until the start is set by hand', async () => {
    const { user } = await renderMedications()
    const form = await open(user, copy.schedule.change, copy.changeSchedule.title)
    const ends = within(form).getByLabelText(copy.changeSchedule.endsOn)
    const starts = within(form).getByLabelText(copy.changeSchedule.startsOnLabel)

    await replace(user, ends, '2026-10-30')
    expect(starts).toHaveValue('2026-10-31')
    expect(within(form).getByText(copy.changeSchedule.startsOn('31 October'))).toBeInTheDocument()

    await replace(user, starts, '2026-11-05')
    await replace(user, ends, '2026-11-01')
    expect(starts).toHaveValue('2026-11-05')
  })

  it('says exactly what happened when only the end was saved, and Retry sends just the new schedule', async () => {
    let endRequests = 0
    server.use(
      http.patch('/api/v1/schedules/:scheduleId', () => {
        endRequests += 1
      }),
      http.post('/api/v1/medications/:medicationId/schedules', () => problem(503, 'SERVICE_UNAVAILABLE', 'Down'), {
        once: true,
      }),
    )
    const { user } = await renderMedications()
    const form = await open(user, copy.schedule.change, copy.changeSchedule.title)
    await user.click(within(form).getByRole('button', { name: copy.changeSchedule.save }))

    const alert = await within(form).findByRole('alert')
    expect(alert).toHaveTextContent(`${copy.changeSchedule.partial('26 October')} ${copy.error.SERVICE_UNAVAILABLE}`)
    expect(alert).toHaveTextContent(copy.error.supportReference(TRACE_ID))
    expect(within(form).getByLabelText(copy.changeSchedule.endsOn)).toHaveAttribute('readonly')

    await user.click(within(form).getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByText(copy.changeSchedule.done('27 October'))).toBeInTheDocument()
    expect(endRequests).toBe(1)
  })

  it('explains an overlap when the new schedule would start before the old one ends (AC-34)', async () => {
    const { user } = await renderMedications()
    const form = await open(user, copy.schedule.change, copy.changeSchedule.title)
    await replace(user, within(form).getByLabelText(copy.changeSchedule.startsOnLabel), '2026-10-26')
    await user.click(within(form).getByRole('button', { name: copy.changeSchedule.save }))

    const alert = await within(form).findByRole('alert')
    expect(alert).toHaveTextContent(copy.error.SCHEDULE_OVERLAP)
    expect(alert).not.toHaveTextContent(/Support reference/)
  })
})
