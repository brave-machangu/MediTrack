import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA, TRACE_ID } from '../../mocks/data'
import { problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const createPath = '/api/v1/patients/:patientId/medications'

async function renderMedications() {
  const view = renderApp(`/patients/${patientA.id}/medications`)
  await screen.findByRole('article', { name: 'Demo Med Alpha' })
  return view
}

async function openAddForm() {
  const view = await renderMedications()
  await view.user.click(screen.getByRole('button', { name: copy.meds.add }))
  return { ...view, form: screen.getByRole('form', { name: copy.medForm.addTitle }) }
}

describe('Medication form', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('adds a medication and confirms it in words that stay on screen', async () => {
    const { user, form } = await openAddForm()
    expect(within(form).getByRole('heading', { name: copy.medForm.addTitle })).toHaveFocus()

    await user.type(within(form).getByLabelText(copy.medForm.name), 'Demo Med Zeta')
    await user.type(within(form).getByLabelText(copy.medForm.dosage), '2 tablets')
    await user.type(within(form).getByLabelText(`${copy.medForm.instructions} ${copy.form.optional}`), 'At night')
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))

    const notice = await screen.findByText(copy.medForm.added('Demo Med Zeta'))
    expect(notice.closest('[tabindex="-1"]')).toHaveFocus()
    const zeta = within(screen.getByRole('article', { name: 'Demo Med Zeta' }))
    expect(zeta.getByText('2 tablets')).toBeInTheDocument()
    expect(zeta.getByText(copy.meds.noSchedule)).toBeInTheDocument()
  })

  it('explains missing fields next to them and in a summary that takes focus, keeping what was typed (AC-03)', async () => {
    const { user, form } = await openAddForm()
    await user.type(within(form).getByLabelText(`${copy.medForm.instructions} ${copy.form.optional}`), 'With food')
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))

    const summary = within(form).getByRole('group', { name: copy.form.errorSummaryTitle })
    expect(summary).toHaveFocus()
    const nameInput = within(form).getByLabelText(copy.medForm.name)
    expect(nameInput).toHaveAttribute('aria-invalid', 'true')
    expect(nameInput).toHaveAccessibleDescription(`${copy.medForm.nameHint} ${copy.form.errorPrefix} ${copy.medForm.nameRequired}`)
    expect(within(form).getByLabelText(`${copy.medForm.instructions} ${copy.form.optional}`)).toHaveValue('With food')

    await user.click(within(summary).getByRole('link', { name: copy.medForm.dosageRequired }))
    expect(within(form).getByLabelText(copy.medForm.dosage)).toHaveFocus()
  })

  it('says when a name is too long', async () => {
    const { user, form } = await openAddForm()
    await user.type(within(form).getByLabelText(copy.medForm.name), 'x'.repeat(101))
    await user.type(within(form).getByLabelText(copy.medForm.dosage), '1 tablet')
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))

    expect(within(form).getByRole('link', { name: copy.medForm.nameTooLong })).toBeInTheDocument()
  })

  it("shows the server's field errors next to the field (AC-03)", async () => {
    server.use(
      http.post(createPath, () =>
        HttpResponse.json(
          { title: 'Invalid', status: 422, code: 'VALIDATION_ERROR', errors: [{ field: 'name', message: 'Name is already used.' }] },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )
    const { user, form } = await openAddForm()
    await user.type(within(form).getByLabelText(copy.medForm.name), 'Demo Med Alpha')
    await user.type(within(form).getByLabelText(copy.medForm.dosage), '1 tablet')
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))

    expect(await within(form).findByRole('link', { name: 'Name is already used.' })).toBeInTheDocument()
    expect(within(form).getByLabelText(copy.medForm.name)).toHaveAccessibleDescription(
      `${copy.medForm.nameHint} ${copy.form.errorPrefix} Name is already used.`,
    )
  })

  it('explains a failed save with the support reference and keeps the form filled', async () => {
    server.use(http.post(createPath, () => problem(503, 'SERVICE_UNAVAILABLE', 'Down'), { once: true }))
    const { user, form } = await openAddForm()
    await user.type(within(form).getByLabelText(copy.medForm.name), 'Demo Med Zeta')
    await user.type(within(form).getByLabelText(copy.medForm.dosage), '1 tablet')
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))

    const alert = await within(form).findByRole('alert')
    expect(alert).toHaveTextContent(copy.error.SERVICE_UNAVAILABLE)
    expect(alert).toHaveTextContent(copy.error.supportReference(TRACE_ID))
    expect(within(form).getByLabelText(copy.medForm.name)).toHaveValue('Demo Med Zeta')
  })

  it('edits a medication in place', async () => {
    const { user } = await renderMedications()
    await user.click(screen.getByRole('button', { name: copy.meds.edit, description: 'Demo Med Beta' }))

    const form = screen.getByRole('form', { name: copy.medForm.editTitle('Demo Med Beta') })
    const dosage = within(form).getByLabelText(copy.medForm.dosage)
    expect(dosage).toHaveValue('1 tablet')
    await user.clear(dosage)
    await user.type(dosage, '2 tablets')
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))

    expect(await screen.findByText(copy.medForm.saved)).toBeInTheDocument()
    expect(within(screen.getByRole('article', { name: 'Demo Med Beta' })).getByText('2 tablets')).toBeInTheDocument()
  })

  it('returns focus to the button that opened the form on Cancel', async () => {
    const { user, form } = await openAddForm()
    await user.click(within(form).getByRole('button', { name: copy.action.cancel }))
    expect(screen.getByRole('button', { name: copy.meds.add })).toHaveFocus()

    await user.click(screen.getByRole('button', { name: copy.meds.edit, description: 'Demo Med Gamma' }))
    await user.click(screen.getByRole('button', { name: copy.action.cancel }))
    expect(screen.getByRole('button', { name: copy.meds.edit, description: 'Demo Med Gamma' })).toHaveFocus()
  })

  it('offers no edit for a stopped medication', async () => {
    const { user } = await renderMedications()
    await user.click(screen.getByRole('checkbox', { name: copy.meds.showStopped }))
    const epsilon = screen.getByRole('article', { name: 'Demo Med Epsilon' })
    expect(within(epsilon).queryByRole('button', { name: copy.meds.edit })).not.toBeInTheDocument()
  })

  it('has no serious or critical axe violations with errors showing', async () => {
    const { user, form } = await openAddForm()
    await user.click(within(form).getByRole('button', { name: copy.medForm.save }))
    expect(await seriousAxeViolations()).toEqual([])
  })
})
