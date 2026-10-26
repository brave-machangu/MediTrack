import { screen, within } from '@testing-library/react'
import { http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../../copy'
import { MOCK_NOW, patientA, TRACE_ID } from '../../mocks/data'
import { problem } from '../../mocks/handlers'
import { server } from '../../mocks/server'
import { renderApp } from '../../test/renderApp'
import { setClock } from '../today/todayTestHelpers'

const stopButton = (name: string) => screen.getByRole('button', { name: copy.meds.stop, description: name })

async function openStopDialog(name = 'Demo Med Alpha') {
  const view = renderApp(`/patients/${patientA.id}/medications`)
  await screen.findByRole('article', { name })
  await view.user.click(stopButton(name))
  return { ...view, dialog: screen.getByRole('dialog', { name: copy.stopConfirm.title(name) }) }
}

describe('Stop medication', () => {
  beforeEach(() => {
    setClock(MOCK_NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('asks first, naming the medication and what will happen, with focus on Cancel', async () => {
    const { dialog } = await openStopDialog()

    expect(dialog).toHaveAccessibleDescription(copy.stopConfirm.body)
    expect(within(dialog).getByRole('button', { name: copy.action.cancel })).toHaveFocus()
  })

  it('stops the medication, says so, and keeps it under stopped medications', async () => {
    const { user, dialog } = await openStopDialog()

    await user.click(within(dialog).getByRole('button', { name: copy.stopConfirm.confirm }))

    const notice = await screen.findByText(copy.meds.stopped('Demo Med Alpha'))
    expect(notice.closest('[tabindex="-1"]')).toHaveFocus()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByRole('article', { name: 'Demo Med Alpha' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: copy.meds.showStopped }))
    const alpha = within(screen.getByRole('article', { name: 'Demo Med Alpha' }))
    expect(alpha.getByText(copy.meds.stoppedOn('26 October'))).toBeInTheDocument()
    expect(alpha.queryByRole('button', { name: copy.meds.stop })).not.toBeInTheDocument()
  })

  it('changes nothing on Cancel and puts focus back on Stop medication', async () => {
    const { user, dialog } = await openStopDialog()

    await user.click(within(dialog).getByRole('button', { name: copy.action.cancel }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(stopButton('Demo Med Alpha')).toHaveFocus()
  })

  it('keeps the dialog open with the reason when stopping fails', async () => {
    server.use(http.patch('/api/v1/medications/:medicationId', () => problem(503, 'SERVICE_UNAVAILABLE', 'Down')))
    const { user, dialog } = await openStopDialog()

    await user.click(within(dialog).getByRole('button', { name: copy.stopConfirm.confirm }))

    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent(copy.error.SERVICE_UNAVAILABLE)
    expect(alert).toHaveTextContent(copy.error.supportReference(TRACE_ID))
    expect(screen.getByRole('article', { name: 'Demo Med Alpha' })).toBeInTheDocument()
  })
})
