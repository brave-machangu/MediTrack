import { useId, useRef } from 'react'
import type { PlannedDose } from '../../api/doses'
import { copy } from '../../copy'
import { formatTime } from '../../dates'
import { StatusBadge } from '../StatusBadge/StatusBadge'
import { DoseActions } from './DoseActions'
import styles from './DoseCard.module.css'

type Props = {
  dose: PlannedDose
  patientId: string
  /** The patient's timezone, for instants such as `log_window_opens_at`. */
  timeZone: string
  at: Date
}

/** One planned dose. Shows only what the API returned; it never works out a status itself. */
export function DoseCard({ dose, patientId, timeZone, at }: Props) {
  const headingId = useId()
  const headingRef = useRef<HTMLHeadingElement>(null)
  return (
    <article className={styles.card} aria-labelledby={headingId}>
      <time className={styles.time} dateTime={dose.scheduled_for}>
        {dose.local_time}
      </time>
      <div className={styles.badge}>
        <StatusBadge status={dose.status} late={dose.late} />
      </div>
      <div className={styles.body}>
        <h3 id={headingId} ref={headingRef} tabIndex={-1}>
          {dose.medication_name}
        </h3>
        <p>{dose.dosage_label}</p>
        {dose.instructions ? <p>{dose.instructions}</p> : null}
        {statusNotes(dose, timeZone, at).map((note) => (
          <p key={note} className={styles.note}>
            {note}
          </p>
        ))}
      </div>
      <DoseActions
        dose={dose}
        patientId={patientId}
        timeZone={timeZone}
        at={at}
        focusHeading={() => headingRef.current?.focus()}
      />
    </article>
  )
}

/** Notes for a dose with no record. DoseActions shows the result line of a recorded dose. */
function statusNotes(dose: PlannedDose, timeZone: string, at: Date): string[] {
  if (dose.status === 'taken' || dose.status === 'skipped') return []
  const notes: string[] = dose.status === 'missed' ? [copy.dose.noRecord] : []
  if (at.getTime() < Date.parse(dose.log_window_opens_at)) {
    notes.push(copy.dose.recordFrom(formatTime(dose.log_window_opens_at, timeZone)))
  } else if (at.getTime() > Date.parse(dose.log_window_closes_at)) {
    notes.push(copy.dose.windowClosed)
  }
  return notes
}
