import { screen, within } from '@testing-library/react'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { copy } from '../../copy'
import { patientA, patientB } from '../../mocks/data'
import { json, problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'

const switchButton = () => screen.getByRole('button', { name: copy.patient.switch })

async function renderMedicationsOfA() {
  const view = renderApp(`/patients/${patientA.id}/medications`)
  await screen.findByText(copy.patient.current(patientA.display_name))
  return view
}

describe('Patient switcher', () => {
  it('opens a list of the other patients and All patients, and says it is open', async () => {
    const { user } = await renderMedicationsOfA()
    expect(switchButton()).toHaveAttribute('aria-expanded', 'false')

    await user.click(switchButton())

    expect(switchButton()).toHaveAttribute('aria-expanded', 'true')
    const list = await screen.findByRole('list', { name: copy.patient.switch })
    const links = within(list).getAllByRole('link').map((link) => link.textContent)
    expect(links).toEqual([patientB.display_name, copy.patient.allPatients])
  })

  it('opens the same page for the chosen patient, closed again', async () => {
    const { user } = await renderMedicationsOfA()
    await user.click(switchButton())
    await user.click(await screen.findByRole('link', { name: patientB.display_name }))

    expect(await screen.findByText(copy.patient.current(patientB.display_name))).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: copy.meds.title })).toBeInTheDocument()
    expect(switchButton()).toHaveAttribute('aria-expanded', 'false')
  })

  it('closes on Esc and puts focus back on the button', async () => {
    const { user } = await renderMedicationsOfA()
    await user.click(switchButton())
    await screen.findByRole('link', { name: patientB.display_name })

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('link', { name: patientB.display_name })).not.toBeInTheDocument()
    expect(switchButton()).toHaveFocus()
  })

  it('is not offered when there is only one patient', async () => {
    server.use(http.get('/api/v1/patients', () => json([patientA])))
    renderApp(`/patients/${patientA.id}/today`)
    await screen.findByText(copy.patient.current(patientA.display_name))
    await screen.findByRole('heading', { level: 1, name: /^Today/ })
    expect(screen.queryByRole('button', { name: copy.patient.switch })).not.toBeInTheDocument()
  })

  it('says when the patient list could not be loaded, with Retry', async () => {
    server.use(http.get('/api/v1/patients', () => problem(503, 'SERVICE_UNAVAILABLE', 'Down'), { once: true }))
    const { user } = await renderMedicationsOfA()
    await user.click(switchButton())

    expect(await screen.findByText(copy.patient.switchError)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByRole('link', { name: patientB.display_name })).toBeInTheDocument()
  })

  it('has no serious or critical axe violations while open', async () => {
    const { user } = await renderMedicationsOfA()
    await user.click(switchButton())
    await screen.findByRole('link', { name: patientB.display_name })
    expect(await seriousAxeViolations()).toEqual([])
  })
})
