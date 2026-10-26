import { BellRing, CircleAlert, CircleCheck, CircleMinus, Clock, ClockCheck, type LucideIcon } from 'lucide-react'
import type { PlannedDose } from '../../api/doses'
import { copy } from '../../copy'
import styles from './StatusBadge.module.css'

type Badge = { label: string; Icon: LucideIcon; className: string | undefined }

// DESIGN.md §3. The label and icon carry the meaning; colour and badge style only reinforce it (AC-28).
const badges: Record<PlannedDose['status'], Badge> = {
  upcoming: { label: copy.status.upcoming, Icon: Clock, className: styles.upcoming },
  due: { label: copy.status.due, Icon: BellRing, className: styles.due },
  missed: { label: copy.status.missed, Icon: CircleAlert, className: styles.missed },
  taken: { label: copy.status.taken, Icon: CircleCheck, className: styles.taken },
  skipped: { label: copy.status.skipped, Icon: CircleMinus, className: styles.skipped },
}

// Only late *taken* doses get their own label (AC-15, DD-3).
const takenLate: Badge = { label: copy.status.takenLate, Icon: ClockCheck, className: styles.taken }

export function StatusBadge({ status, late }: Pick<PlannedDose, 'status' | 'late'>) {
  const { label, Icon, className } = status === 'taken' && late ? takenLate : badges[status]
  return (
    <span className={`${styles.badge} ${className ?? ''}`}>
      <Icon aria-hidden="true" className={styles.icon} />
      {label}
    </span>
  )
}
