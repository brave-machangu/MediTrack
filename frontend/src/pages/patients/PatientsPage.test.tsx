import { screen, within } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { copy } from '../../copy'
import { patientA, patientB, TRACE_ID } from '../../mocks/data'
import { json, problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'

async function renderPatients() {
  const view = renderApp('/')
  await screen.findByRole('link', { name: patientA.display_name })
  return view
}

async function replace(user: UserEvent, input: HTMLElement, value: string) {
  await user.clear(input)
  if (value !== '') await user.type(input, value)
}

const editButton = (name: string) => screen.getByRole('button', { name: copy.patients.edit, description: name })

describe('Patients page', () => {
  it('lists patients by name with their timezone, each opening their Today page', async () => {
    await renderPatients()

    const items = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(items.map((item) => within(item).getByRole('link').textContent)).toEqual([patientA.display_name, patientB.display_name])
    expect(within(items[1] ?? document.body).getByText('America/New York')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: patientA.display_name })).toHaveAttribute('href', `/patients/${patientA.id}/today`)
  })

  it('adds a patient, suggesting the browser timezone', async () => {
    const { user } = await renderPatients()
    await user.click(screen.getByRole('button', { name: copy.patients.add }))
    const form = screen.getByRole('form', { name: copy.patientForm.addTitle })
    expect(within(form).getByRole('heading', { name: copy.patientForm.addTitle })).toHaveFocus()
    expect(within(form).getByLabelText(copy.patientForm.timezone)).toHaveValue('Asia/Tokyo')

    await user.type(within(form).getByLabelText(copy.patientForm.name), 'Demo Patient C')
    await user.selectOptions(within(form).getByLabelText(copy.patientForm.timezone), 'Europe/London')
    await user.click(within(form).getByRole('button', { name: copy.patientForm.save }))

    expect(await screen.findByText(copy.patientForm.added('Demo Patient C'))).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Demo Patient C' })).toBeInTheDocument()
    expect(screen.getByText('Europe/London')).toBeInTheDocument()
  })

  it('explains a missing or too-long name next to the field and in a summary', async () => {
    const { user } = await renderPatients()
    await user.click(screen.getByRole('button', { name: copy.patients.add }))
    const form = screen.getByRole('form', { name: copy.patientForm.addTitle })

    await user.click(within(form).getByRole('button', { name: copy.patientForm.save }))
    expect(within(form).getByRole('group', { name: copy.form.errorSummaryTitle })).toHaveFocus()
    expect(within(form).getByLabelText(copy.patientForm.name)).toHaveAccessibleDescription(
      `${copy.patientForm.nameHint} ${copy.form.errorPrefix} ${copy.patientForm.nameRequired}`,
    )

    await user.type(within(form).getByLabelText(copy.patientForm.name), 'x'.repeat(81))
    await user.click(within(form).getByRole('button', { name: copy.patientForm.save }))
    expect(within(form).getByRole('link', { name: copy.patientForm.nameTooLong })).toBeInTheDocument()
  })

  it("shows the server's timezone error next to the Timezone field (AC-02)", async () => {
    server.use(
      http.post('/api/v1/patients', () =>
        HttpResponse.json(
          { title: 'Invalid', status: 422, code: 'VALIDATION_ERROR', errors: [{ field: 'timezone', message: 'Not a valid IANA timezone.' }] },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )
    const { user } = await renderPatients()
    await user.click(screen.getByRole('button', { name: copy.patients.add }))
    const form = screen.getByRole('form', { name: copy.patientForm.addTitle })
    await user.type(within(form).getByLabelText(copy.patientForm.name), 'Demo Patient C')
    await user.click(within(form).getByRole('button', { name: copy.patientForm.save }))

    expect(await within(form).findByRole('link', { name: 'Not a valid IANA timezone.' })).toBeInTheDocument()
    expect(within(form).getByLabelText(copy.patientForm.timezone)).toHaveAttribute('aria-invalid', 'true')
  })

  it("edits a patient's name", async () => {
    const { user } = await renderPatients()
    await user.click(editButton(patientB.display_name))
    const form = screen.getByRole('form', { name: copy.patientForm.editTitle(patientB.display_name) })

    await replace(user, within(form).getByLabelText(copy.patientForm.name), 'Demo Patient Bea')
    await user.click(within(form).getByRole('button', { name: copy.patientForm.save }))

    expect(await screen.findByText(copy.patientForm.saved('Demo Patient Bea'))).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Demo Patient Bea' })).toBeInTheDocument()
  })

  it('explains next to Timezone that it cannot change once doses are recorded, keeping the form filled', async () => {
    const { user } = await renderPatients()
    await user.click(editButton(patientA.display_name))
    const form = screen.getByRole('form', { name: copy.patientForm.editTitle(patientA.display_name) })

    await user.selectOptions(within(form).getByLabelText(copy.patientForm.timezone), 'Europe/London')
    await user.click(within(form).getByRole('button', { name: copy.patientForm.save }))

    expect(await within(form).findByRole('link', { name: copy.error.PATIENT_HAS_LOGS })).toBeInTheDocument()
    expect(within(form).getByLabelText(copy.patientForm.timezone)).toHaveValue('Europe/London')
  })

  it('returns focus to Edit on Cancel', async () => {
    const { user } = await renderPatients()
    await user.click(editButton(patientB.display_name))
    await user.click(screen.getByRole('button', { name: copy.action.cancel }))
    expect(editButton(patientB.display_name)).toHaveFocus()
  })

  it('says what is empty when there are no patients yet', async () => {
    server.use(http.get('/api/v1/patients', () => json([])))
    renderApp('/')
    expect(await screen.findByRole('heading', { level: 2, name: copy.patients.empty.title })).toBeInTheDocument()
    expect(screen.getByText(copy.patients.empty.body)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: copy.patients.add })).toBeInTheDocument()
  })

  it('explains a failed load with the support reference, and Retry loads the list', async () => {
    server.use(http.get('/api/v1/patients', () => problem(503, 'SERVICE_UNAVAILABLE', 'Down'), { once: true }))
    const { user } = renderApp('/')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(copy.patients.error.title)
    expect(alert).toHaveTextContent(copy.error.supportReference(TRACE_ID))
    await user.click(within(alert).getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByRole('link', { name: patientA.display_name })).toBeInTheDocument()
  })

  it('has no serious or critical axe violations', async () => {
    await renderPatients()
    expect(await seriousAxeViolations()).toEqual([])
  })
})
