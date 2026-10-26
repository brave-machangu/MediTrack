import { screen, within } from '@testing-library/react'
import { delay, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { medicationsA, MOCK_NOW, patientA, patientB, TRACE_ID } from '../../mocks/data'
import { json, problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const medicationsPath = '/api/v1/patients/:patientId/medications'
const pageA = `/patients/${patientA.id}/medications`
const medication = (name: string) => screen.getByRole('article', { name })

async function renderMedications(path = pageA) {
  const view = renderApp(path)
  await screen.findByRole('article', { name: 'Demo Med Alpha' })
  return view
}

describe('Medications page', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('lists current medications by name, with dosage, instructions and schedules in plain words', async () => {
    await renderMedications()

    const names = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(names).toEqual(['Demo Med Alpha', 'Demo Med Beta', 'Demo Med Delta Extended Release Capsules', 'Demo Med Gamma'])

    const alpha = within(medication('Demo Med Alpha'))
    for (const text of ['500 mg, 1 tablet', 'With food', '07:00 and 14:00', copy.schedule.everyDay]) {
      expect(alpha.getByText(text)).toBeInTheDocument()
    }
    expect(alpha.getByText(copy.schedule.from('1 October'))).toBeInTheDocument()
    expect(alpha.getByText(copy.schedule.grace(60))).toBeInTheDocument()
    expect(within(medication('Demo Med Beta')).getByText(copy.schedule.weekdays)).toBeInTheDocument()
  })

  it('shows stopped medications only when asked, with the date they were stopped', async () => {
    const { user } = await renderMedications()
    expect(screen.queryByRole('article', { name: 'Demo Med Epsilon' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: copy.meds.showStopped }))

    const epsilon = within(medication('Demo Med Epsilon'))
    expect(epsilon.getByText(copy.meds.stoppedOn('12 October'))).toBeInTheDocument()
    expect(epsilon.getByText(copy.schedule.fromTo('1 September', '12 October'))).toBeInTheDocument()
  })

  it('says when a medication has no schedule yet', async () => {
    const [alpha] = medicationsA
    if (alpha === undefined) throw new Error('mock has no medications')
    server.use(http.get(medicationsPath, () => json([{ ...alpha, schedules: [] }])))
    await renderMedications()

    expect(within(medication('Demo Med Alpha')).getByText(copy.meds.noSchedule)).toBeInTheDocument()
  })

  it('says what is empty when the patient has no medications, without the stopped toggle', async () => {
    renderApp(`/patients/${patientB.id}/medications`)

    expect(await screen.findByRole('heading', { level: 2, name: copy.meds.empty.title })).toBeInTheDocument()
    expect(screen.getByText(copy.meds.empty.body)).toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('says the list is loading in words', async () => {
    server.use(
      http.get(medicationsPath, async () => {
        await delay('infinite')
      }),
    )
    renderApp(pageA)
    expect(await screen.findByText(copy.meds.loading)).toHaveAttribute('role', 'status')
  })

  it('explains a failed load with the support reference, and Retry loads the list', async () => {
    server.use(http.get(medicationsPath, () => problem(503, 'SERVICE_UNAVAILABLE', 'Down'), { once: true }))
    const { user } = renderApp(pageA)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(copy.meds.error.title)
    expect(alert).toHaveTextContent(copy.error.supportReference(TRACE_ID))
    await user.click(within(alert).getByRole('button', { name: copy.action.retry }))
    expect(await screen.findByRole('article', { name: 'Demo Med Alpha' })).toBeInTheDocument()
  })

  it('has no serious or critical axe violations', async () => {
    await renderMedications()
    expect(await seriousAxeViolations()).toEqual([])
  })
})
