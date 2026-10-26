import { useId } from 'react'
import type { Schedule } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { copy } from '../../copy'
import styles from './medications.module.css'
import { datesText, daysText, timesText } from './scheduleText'
import type { OpenForm, OpenFormState } from './useOpenForm'

type Props = Pick<OpenFormState, 'focusIf'> & {
  schedule: Schedule
  currentYear: string | undefined
  /** False for a stopped medication's schedules, which are read-only. */
  current: boolean
  openForm: (form: OpenForm) => void
}

/** One schedule in plain words, with what can be done to it (requirements §4.4). */
export function ScheduleItem({ schedule, currentYear, current, focusIf, openForm }: Props) {
  const timesId = useId()
  const { id } = schedule
  // The description (the schedule's times) says which schedule each action is for.
  const action = (kind: Exclude<NonNullable<OpenForm>['kind'], 'add' | 'add-schedule'>, label: string, danger = false) => (
    <Button
      ref={focusIf(`${kind}-${id}`)}
      variant="quiet"
      aria-describedby={timesId}
      className={`${styles.quietAction ?? ''} ${danger ? (styles.dangerText ?? '') : ''}`}
      onClick={() => {
        openForm({ kind, id })
      }}
    >
      {label}
    </Button>
  )

  return (
    <div className={styles.details}>
      <p id={timesId} className={styles.times}>
        {timesText(schedule.times_of_day)}
      </p>
      <p>{daysText(schedule.days_of_week)}</p>
      <p>{datesText(schedule, currentYear)}</p>
      <p>{copy.schedule.grace(schedule.grace_period_minutes)}</p>
      {!current ? null : schedule.has_dose_logs ? (
        <>
          <p className={styles.note}>{copy.schedule.hasLogs}</p>
          <div className={styles.inlineActions}>
            {action('change-schedule', copy.schedule.change)}
            {action('end-schedule', copy.schedule.changeEnd)}
          </div>
        </>
      ) : (
        <div className={styles.inlineActions}>
          {action('edit-schedule', copy.schedule.edit)}
          {action('delete-schedule', copy.schedule.delete, true)}
        </div>
      )}
    </div>
  )
}
