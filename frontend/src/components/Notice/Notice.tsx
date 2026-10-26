import { CircleAlert, CircleCheck, Info, TriangleAlert, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import styles from './Notice.module.css'

type Tone = 'info' | 'success' | 'warning' | 'error'

const tones: Record<Tone, { Icon: LucideIcon; className: string | undefined; role: 'status' | 'alert' }> = {
  info: { Icon: Info, className: styles.info, role: 'status' },
  success: { Icon: CircleCheck, className: styles.success, role: 'status' },
  warning: { Icon: TriangleAlert, className: styles.warning, role: 'status' },
  error: { Icon: CircleAlert, className: styles.error, role: 'alert' },
}

/** A message that stays until the situation changes. Never dismissed on a timer. */
export function Notice({ tone, children }: { tone: Tone; children: ReactNode }) {
  const { Icon, className, role } = tones[tone]
  return (
    <div role={role} className={`${styles.notice} ${className ?? ''}`}>
      <Icon aria-hidden="true" className={styles.icon} />
      <div className={styles.body}>{children}</div>
    </div>
  )
}
