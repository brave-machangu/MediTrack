import type { ReactNode } from 'react'
import type { Medication } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { copy } from '../../copy'
import { formatShortDate, localDate } from '../../dates'
import styles from './medications.module.css'

/** The medication's heading id, so actions elsewhere on the card can be described by its name. */
export const medicationHeadingId = (medicationId: string) => `medication-${medicationId}`

type Props = {
  medication: Medication
  /** The patient's timezone, for `deactivated_at`. */
  timeZone: string | undefined
  currentYear: string | undefined
  /** Only current medications can be edited. */
  onEdit?: (() => void) | undefined
  onStop?: (() => void) | undefined
  /** Ref callbacks that put focus back on Edit or Stop when a form or dialog closes. */
  editRef?: ((element: HTMLElement | null) => void) | undefined
  stopRef?: ((element: HTMLElement | null) => void) | undefined
  /** The schedules section (ScheduleSection). */
  children: ReactNode
}

/** One medication: name, dosage, instructions, its schedules, and Edit and Stop while it's current. */
export function MedicationItem(props: Props) {
  const { medication, timeZone, currentYear, onEdit, onStop, editRef, stopRef, children } = props
  const headingId = medicationHeadingId(medication.id)
  const stoppedOn =
    !medication.active && medication.deactivated_at && timeZone !== undefined
      ? copy.meds.stoppedOn(formatShortDate(localDate(medication.deactivated_at, timeZone), currentYear))
      : null

  return (
    <article aria-labelledby={headingId} className={styles.medication}>
      <div className={styles.details}>
        <h2 id={headingId} className={styles.name}>
          {medication.name}
        </h2>
        {/* Straight under the name, so a stopped medication can't be mistaken for a current one. */}
        {stoppedOn === null ? null : <p className={styles.note}>{stoppedOn}</p>}
        <p>{medication.dosage_label}</p>
        {medication.instructions ? <p>{medication.instructions}</p> : null}
      </div>
      {onEdit === undefined ? null : (
        // Quiet, so a list of medications isn't a wall of buttons. The visible label is the same on every
        // medication; the description says which one.
        <Button
          ref={editRef}
          variant="quiet"
          aria-describedby={headingId}
          className={styles.quietAction}
          onClick={onEdit}
        >
          {copy.meds.edit}
        </Button>
      )}
      {children}
      {onStop === undefined ? null : (
        <Button
          ref={stopRef}
          variant="quiet"
          aria-describedby={headingId}
          className={`${styles.quietAction ?? ''} ${styles.dangerText ?? ''}`}
          onClick={onStop}
        >
          {copy.meds.stop}
        </Button>
      )}
    </article>
  )
}
