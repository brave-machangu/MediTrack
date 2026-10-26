import { isLogWindowOpen, type PlannedDose } from '../../api/doses'
import type { copy } from '../../copy'

export type GroupId = keyof typeof copy.today.group

export const groupOrder: readonly GroupId[] = ['attention', 'later', 'done', 'missed']

/**
 * DESIGN.md §4.1. Uses the server's status as given; the log window only separates missed doses
 * that can still be recorded (Needs attention) from those that can't (Missed).
 */
export function groupOf(dose: PlannedDose, at: Date): GroupId {
  switch (dose.status) {
    case 'due':
      return 'attention'
    case 'missed':
      return isLogWindowOpen(dose, at) ? 'attention' : 'missed'
    case 'upcoming':
      return 'later'
    case 'taken':
    case 'skipped':
      return 'done'
  }
}
