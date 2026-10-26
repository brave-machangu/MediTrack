import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { copy } from '../../copy'
import { patientA } from '../../mocks/data'
import { seriousAxeViolations } from '../../test/axe'
import { renderApp } from '../../test/renderApp'

const patientPages = ['today', 'medications', 'missed', 'summary'].map((page) => `/patients/${patientA.id}/${page}`)
const everyPage = ['/', ...patientPages, '/no-such-page']

describe('AppShell', () => {
  it.each(everyPage)('shows the demo notice and the disclaimer on %s (AC-27, AC-40)', async (path) => {
    renderApp(path)
    await screen.findByRole('heading', { level: 1 })

    const demoNotice = screen.getByRole('note', { name: copy.app.demoBannerLabel })
    expect(demoNotice).toHaveTextContent(copy.app.demoBanner)
    expect(within(screen.getByRole('contentinfo')).getByText(copy.app.disclaimer)).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
  })

  it('names the patient and marks the current page in the navigation', async () => {
    renderApp(`/patients/${patientA.id}/missed`)

    expect(await screen.findByText(copy.patient.current(patientA.display_name))).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: copy.app.navLabel })
    expect(within(nav).getByRole('link', { name: copy.nav.missed })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: copy.nav.today })).not.toHaveAttribute('aria-current')
    expect(document.title).toBe(copy.doc.title(copy.nav.missed, patientA.display_name))
  })

  it('offers a skip link as the first stop for keyboard users', async () => {
    const { user } = renderApp(`/patients/${patientA.id}/today`)
    await screen.findByRole('heading', { level: 1 })

    await user.tab()
    const skipLink = screen.getByRole('link', { name: copy.app.skipLink })
    expect(skipLink).toHaveFocus()
    expect(skipLink).toHaveAttribute('href', '#main')
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main')
  })

  it('moves focus to the new page heading after navigating', async () => {
    const { user } = renderApp(`/patients/${patientA.id}/today`)
    await screen.findByText(copy.patient.current(patientA.display_name))

    await user.click(screen.getByRole('link', { name: copy.nav.medications }))
    expect(await screen.findByRole('heading', { level: 1, name: copy.meds.title })).toHaveFocus()
  })

  it('explains when the patient no longer exists and hides the patient navigation', async () => {
    renderApp('/patients/00000000-0000-4000-8000-000000000000/today')

    expect(await screen.findByText(copy.error.NOT_FOUND)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: copy.notFound.title })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: copy.notFound.action })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('navigation', { name: copy.app.navLabel })).not.toBeInTheDocument()
  })

  it('has no serious or critical axe violations on a patient page', async () => {
    renderApp(`/patients/${patientA.id}/today`)
    await screen.findByText(copy.patient.current(patientA.display_name))

    expect(await seriousAxeViolations()).toEqual([])
  })
})
