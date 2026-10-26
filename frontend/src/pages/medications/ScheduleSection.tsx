import { Plus } from 'lucide-react'
import type { Medication } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { copy } from '../../copy'
import styles from './medications.module.css'
import { ChangeScheduleForm } from './ChangeScheduleForm'
import { EndDateForm } from './EndDateForm'
import { medicationHeadingId } from './MedicationItem'
import { ScheduleForm } from './ScheduleForm'
import { ScheduleItem } from './ScheduleItem'
import type { OpenForm, OpenFormState } from './forms'

type Props = Pick<OpenFormState, 'open' | 'focusIf' | 'cancel' | 'onSaved'> & {
  medication: Medication
  patientId: string
  openForm: (form: OpenForm) => void
  /** The patient's today: the default start of a new schedule. */
  today: string | undefined
  currentYear: string | undefined
}

/** A medication's schedules, each replaced by its form while one is open, and Add a schedule while it's current. */
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
          {medication.schedules.map((schedule) => {
            // Which form, if any, is open on this schedule.
            const formHere = open !== null && 'id' in open && open.id === schedule.id ? open.kind : null
            return (
              <li key={schedule.id}>
                {formHere === 'edit-schedule' ? (
                  <ScheduleForm {...formProps} schedule={schedule} onCancel={cancel(`edit-schedule-${schedule.id}`)} />
                ) : formHere === 'change-schedule' ? (
                  <ChangeScheduleForm
                    {...{ patientId, medication, schedule, today, currentYear, onSaved }}
                    onCancel={cancel(`change-schedule-${schedule.id}`)}
                  />
                ) : formHere === 'end-schedule' ? (
                  <EndDateForm
                    {...{ patientId, schedule, today, onSaved }}
                    onCancel={cancel(`end-schedule-${schedule.id}`)}
                  />
                ) : (
                  <ScheduleItem
                    schedule={schedule}
                    currentYear={currentYear}
                    current={medication.active}
                    focusIf={focusIf}
                    openForm={openForm}
                  />
                )}
              </li>
            )
          })}
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
