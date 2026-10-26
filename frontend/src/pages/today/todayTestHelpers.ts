import { screen, within } from '@testing-library/react'
import { vi } from 'vitest'

/** Fixes the time. Only Date is faked, so MSW and Testing Library timers keep working. */
export function setClock(instant: string) {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(instant))
}

/** Medication names of the cards in one group, in screen order. */
export function namesIn(groupName: string): (string | null)[] {
  const list = screen.getByRole('list', { name: groupName })
  return within(list)
    .getAllByRole('heading', { level: 3 })
    .map((heading) => heading.textContent)
}

export function cardIn(groupName: string, index: number): HTMLElement {
  const card = within(screen.getByRole('list', { name: groupName })).getAllByRole('article')[index]
  if (card === undefined) throw new Error(`no card ${String(index)} in ${groupName}`)
  return card
}
