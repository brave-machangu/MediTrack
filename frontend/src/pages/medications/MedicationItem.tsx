import { useId } from 'react'
import type { Medication, Schedule } from '../../api/medications'
import { copy } from '../../copy'
import { formatShortDate, localDate } from '../../dates'
import styles from './medications.module.css'
import { datesText, daysText, timesText } from './scheduleText'

type Props = {
  medication: Medication
  /** The patient's timezone, for `deactivated_at`. */
  timeZone: string | undefined
  currentYear: string | undefined
}

/** One medication and its schedules, in plain words. */
export function MedicationItem({ medication, timeZone, currentYear }: Props) {
  const headingId = useId()
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
      <div className={styles.details}>
        <h3 className={styles.schedulesTitle}>{copy.meds.schedulesTitle}</h3>
        {medication.schedules.length === 0 ? (
          <p>{copy.meds.noSchedule}</p>
        ) : (
          <ul role="list" className={styles.schedules}>
            {medication.schedules.map((schedule) => (
              <li key={schedule.id}>
                <ScheduleSummary schedule={schedule} currentYear={currentYear} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}

function ScheduleSummary({ schedule, currentYear }: { schedule: Schedule; currentYear: string | undefined }) {
  return (
    <div className={styles.details}>
      <p className={styles.times}>{timesText(schedule.times_of_day)}</p>
      <p>{daysText(schedule.days_of_week)}</p>
      <p>{datesText(schedule, currentYear)}</p>
      <p>{copy.schedule.grace(schedule.grace_period_minutes)}</p>
    </div>
  )
}
