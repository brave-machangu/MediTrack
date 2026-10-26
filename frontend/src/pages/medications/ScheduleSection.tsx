import { Plus } from 'lucide-react'
import { useId } from 'react'
import type { Medication, Schedule } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { copy } from '../../copy'
import styles from './medications.module.css'
import { medicationHeadingId } from './MedicationItem'
import { ScheduleForm } from './ScheduleForm'
import { datesText, daysText, timesText } from './scheduleText'
import type { OpenForm, OpenFormState } from './useOpenForm'

type Props = Pick<OpenFormState, 'open' | 'focusIf' | 'cancel' | 'onSaved'> & {
  medication: Medication
  patientId: string
  openForm: (form: OpenForm) => void
  /** The patient's today: the default start of a new schedule. */
  today: string | undefined
  currentYear: string | undefined
}

/** A medication's schedules, with Edit / Delete for those without records and Add a schedule while it's current. */
export function ScheduleSection(props: Props) {
  const { medication, patientId, open, focusIf, cancel, onSaved, openForm, today, currentYear } = props
  const adding = open?.kind === 'add-schedule' && open.medicationId === medication.id
  const formProps = { patientId, medication, defaultStart: today ?? '', onSaved }

  return (
    <div className={styles.details}>
      <h3 className={styles.schedulesTitle}>{copy.meds.schedulesTitle}</h3>
      {medication.schedules.length === 0 && !adding ? <p>{copy.meds.noSchedule}</p> : null}
      {medication.schedules.length === 0 ? null : (
        <ul role="list" className={styles.schedules}>
          {medication.schedules.map((schedule) => (
            <li key={schedule.id}>
              {open?.kind === 'edit-schedule' && open.id === schedule.id ? (
                <ScheduleForm {...formProps} schedule={schedule} onCancel={cancel(`edit-schedule-${schedule.id}`)} />
              ) : (
                <ScheduleItem
                  schedule={schedule}
                  currentYear={currentYear}
                  // Without records a schedule can be edited or deleted freely (requirements §4.4).
                  editable={medication.active && !schedule.has_dose_logs}
                  focusIf={focusIf}
                  openForm={openForm}
                />
              )}
            </li>
          ))}
        </ul>
      )}
      {!medication.active ? null : adding ? (
        <ScheduleForm {...formProps} onCancel={cancel(`add-schedule-${medication.id}`)} />
      ) : (
        <Button
          ref={focusIf(`add-schedule-${medication.id}`)}
          variant="quiet"
          aria-describedby={medicationHeadingId(medication.id)}
          className={styles.quietAction}
          onClick={() => {
            openForm({ kind: 'add-schedule', medicationId: medication.id })
          }}
        >
          <Plus aria-hidden="true" />
          {copy.schedule.add}
        </Button>
      )}
    </div>
  )
}

type ItemProps = Pick<OpenFormState, 'focusIf'> & {
  schedule: Schedule
  currentYear: string | undefined
  editable: boolean
  openForm: (form: OpenForm) => void
}

function ScheduleItem({ schedule, currentYear, editable, focusIf, openForm }: ItemProps) {
  const timesId = useId()
  const { id } = schedule
  return (
    <div className={styles.details}>
      <p id={timesId} className={styles.times}>
        {timesText(schedule.times_of_day)}
      </p>
      <p>{daysText(schedule.days_of_week)}</p>
      <p>{datesText(schedule, currentYear)}</p>
      <p>{copy.schedule.grace(schedule.grace_period_minutes)}</p>
      {editable ? (
        // The description (the schedule's times) says which schedule the action is for.
        <div className={styles.inlineActions}>
          <Button
            ref={focusIf(`edit-schedule-${id}`)}
            variant="quiet"
            aria-describedby={timesId}
            className={styles.quietAction}
            onClick={() => {
              openForm({ kind: 'edit-schedule', id })
            }}
          >
            {copy.schedule.edit}
          </Button>
          <Button
            ref={focusIf(`delete-schedule-${id}`)}
            variant="quiet"
            aria-describedby={timesId}
            className={`${styles.quietAction ?? ''} ${styles.dangerText ?? ''}`}
            onClick={() => {
              openForm({ kind: 'delete-schedule', id })
            }}
          >
            {copy.schedule.delete}
          </Button>
        </div>
      ) : null}
    </div>
  )
}
