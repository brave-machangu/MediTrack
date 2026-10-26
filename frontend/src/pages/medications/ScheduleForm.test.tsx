import { screen, within } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA } from '../../mocks/data'
import { server } from '../../mocks/server'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const delta = 'Demo Med Delta Extended Release Capsules'
const medication = (name: string) => screen.getByRole('article', { name })

async function renderMedications() {
  const view = renderApp(`/patients/${patientA.id}/medications`)
  await screen.findByRole('article', { name: 'Demo Med Alpha' })
  return view
}

async function openAddSchedule(user: UserEvent, name: string) {
  await user.click(screen.getByRole('button', { name: copy.schedule.add, description: name }))
  return screen.getByRole('form', { name: copy.scheduleForm.addTitle(name) })
}

async function replace(user: UserEvent, input: HTMLElement, value: string) {
  await user.clear(input)
  await user.type(input, value)
}

describe('Schedules', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('adds a weekend schedule next to a weekday one, as the overlap rule allows (AC-34)', async () => {
    const { user } = await renderMedications()
    const form = await openAddSchedule(user, 'Demo Med Beta')
    expect(within(form).getByRole('heading', { name: copy.scheduleForm.addTitle('Demo Med Beta') })).toHaveFocus()
    expect(within(form).getByLabelText(copy.scheduleForm.start)).toHaveValue('2026-10-26')

    await replace(user, within(form).getByLabelText(copy.scheduleForm.time(1)), '10:00')
    for (const day of ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']) {
      await user.click(within(form).getByRole('checkbox', { name: day }))
    }
    await replace(user, within(form).getByLabelText(copy.scheduleForm.start), '2026-10-31')
    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.save }))

    expect(await screen.findByText(copy.scheduleForm.added)).toBeInTheDocument()
    const beta = within(medication('Demo Med Beta'))
    expect(beta.getByText('10:00')).toBeInTheDocument()
    expect(beta.getByText(copy.schedule.weekend)).toBeInTheDocument()
  })

  it('explains an overlapping schedule next to the form and keeps what was entered (AC-34)', async () => {
    const { user } = await renderMedications()
    const form = await openAddSchedule(user, delta)
    await replace(user, within(form).getByLabelText(copy.scheduleForm.time(1)), '09:00')
    await replace(user, within(form).getByLabelText(copy.scheduleForm.start), '2026-10-28')
    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.save }))

    const alert = await within(form).findByRole('alert')
    expect(alert).toHaveTextContent(copy.error.SCHEDULE_OVERLAP)
    expect(within(alert).getByText(copy.error.SCHEDULE_OVERLAP)).toHaveFocus()
    expect(within(form).getByLabelText(copy.scheduleForm.time(1))).toHaveValue('09:00')
  })

  it('checks times, days and the grace period before sending (AC-05)', async () => {
    const { user } = await renderMedications()
    const form = await openAddSchedule(user, delta)
    for (const day of ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']) {
      await user.click(within(form).getByRole('checkbox', { name: day }))
    }
    await replace(user, within(form).getByLabelText(copy.scheduleForm.grace), '300')
    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.save }))

    const summary = within(form).getByRole('group', { name: copy.form.errorSummaryTitle })
    expect(summary).toHaveFocus()
    for (const message of [copy.scheduleForm.timeRequired, copy.scheduleForm.daysRequired, copy.scheduleForm.graceRange]) {
      expect(within(summary).getByRole('link', { name: message })).toBeInTheDocument()
    }
    expect(within(form).getByLabelText(copy.scheduleForm.time(1))).toHaveAttribute('aria-invalid', 'true')
    await user.click(within(summary).getByRole('link', { name: copy.scheduleForm.daysRequired }))
    expect(within(form).getByRole('checkbox', { name: 'Monday' })).toHaveFocus()
  })

  it('adds and removes times, moving focus with them', async () => {
    const { user } = await renderMedications()
    const form = await openAddSchedule(user, delta)

    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.addTime }))
    expect(within(form).getByLabelText(copy.scheduleForm.time(2))).toHaveFocus()

    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.removeTimeName(2) }))
    expect(within(form).queryByLabelText(copy.scheduleForm.time(2))).not.toBeInTheDocument()
    expect(within(form).getByLabelText(copy.scheduleForm.time(1))).toHaveFocus()
  })

  it('places a server error on the time it is about', async () => {
    server.use(
      http.post('/api/v1/medications/:medicationId/schedules', () =>
        HttpResponse.json(
          { title: 'Invalid', status: 422, code: 'VALIDATION_ERROR', errors: [{ field: 'times_of_day[0]', message: 'Not a time.' }] },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )
    const { user } = await renderMedications()
    const form = await openAddSchedule(user, 'Demo Med Beta')
    await replace(user, within(form).getByLabelText(copy.scheduleForm.time(1)), '10:00')
    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.save }))

    expect(await within(form).findByRole('link', { name: 'Not a time.' })).toBeInTheDocument()
    expect(within(form).getByLabelText(copy.scheduleForm.time(1))).toHaveAttribute('aria-invalid', 'true')
  })

  it('edits a schedule that has no recorded doses', async () => {
    const { user } = await renderMedications()
    await user.click(within(medication(delta)).getByRole('button', { name: copy.schedule.edit, description: '08:30' }))

    const form = screen.getByRole('form', { name: copy.scheduleForm.editTitle })
    await replace(user, within(form).getByLabelText(copy.scheduleForm.time(1)), '09:00')
    await user.click(within(form).getByRole('button', { name: copy.scheduleForm.save }))

    expect(await screen.findByText(copy.scheduleForm.saved)).toBeInTheDocument()
    expect(within(medication(delta)).getByText('09:00')).toBeInTheDocument()
  })

  it('deletes a schedule that has no recorded doses after saying exactly which one', async () => {
    const { user } = await renderMedications()
    await user.click(within(medication(delta)).getByRole('button', { name: copy.schedule.delete, description: '08:30' }))

    const dialog = screen.getByRole('dialog', { name: copy.deleteSchedule.title })
    expect(dialog).toHaveAccessibleDescription(copy.deleteSchedule.body('08:30, every day, from 26 October, no end date'))
    await user.click(within(dialog).getByRole('button', { name: copy.deleteSchedule.confirm }))

    expect(await screen.findByText(copy.deleteSchedule.done)).toBeInTheDocument()
    expect(within(medication(delta)).getByText(copy.meds.noSchedule)).toBeInTheDocument()
  })

  it('offers no edit or delete for a schedule with recorded doses, and no new schedules on a stopped medication', async () => {
    const { user } = await renderMedications()
    const alpha = within(medication('Demo Med Alpha'))
    expect(alpha.queryByRole('button', { name: copy.schedule.edit })).not.toBeInTheDocument()
    expect(alpha.queryByRole('button', { name: copy.schedule.delete })).not.toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: copy.meds.showStopped }))
    expect(within(medication('Demo Med Epsilon')).queryByRole('button', { name: copy.schedule.add })).not.toBeInTheDocument()
  })
})
