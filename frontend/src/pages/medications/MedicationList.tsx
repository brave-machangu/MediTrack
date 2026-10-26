import type { Medication } from '../../api/medications'
import { MedicationForm } from './MedicationForm'
import { MedicationItem } from './MedicationItem'
import { ScheduleSection } from './ScheduleSection'
import styles from './medications.module.css'
import type { OpenForm, OpenFormState } from './forms'

type Forms = Pick<OpenFormState, 'open' | 'focusIf' | 'cancel' | 'onSaved'>

type Props = Forms & {
  medications: Medication[]
  patientId: string
  openForm: (form: OpenForm) => void
  timeZone: string | undefined
  /** The patient's today ("2026-10-26"), from the server. */
  today: string | undefined
}

/** The medications, with the one being edited replaced by its form. Stopped ones can't be edited or stopped. */
export function MedicationList(props: Props) {
  const { medications, patientId, open, focusIf, cancel, onSaved, openForm, timeZone, today } = props
  const currentYear = today?.slice(0, 4)
  if (medications.length === 0) return null
  return (
    // role="list" because Safari drops list semantics when list-style is none.
    <ul role="list" className={styles.list}>
      {medications.map((medication) => {
        const { id } = medication
        const actions = medication.active
          ? {
              onEdit: () => {
                openForm({ kind: 'edit', id })
              },
              onStop: () => {
                openForm({ kind: 'stop', id })
              },
            }
          : {}
        return (
          <li key={id}>
            {open?.kind === 'edit' && open.id === id ? (
              <MedicationForm
                patientId={patientId}
                medication={medication}
                onSaved={onSaved}
                onCancel={cancel(id)}
              />
            ) : (
              <MedicationItem
                medication={medication}
                timeZone={timeZone}
                currentYear={currentYear}
                editRef={focusIf(id)}
                stopRef={focusIf(`stop-${id}`)}
                {...actions}
              >
                <ScheduleSection
                  medication={medication}
                  patientId={patientId}
                  open={open}
                  focusIf={focusIf}
                  cancel={cancel}
                  onSaved={onSaved}
                  openForm={openForm}
                  today={today}
                  currentYear={currentYear}
                />
              </MedicationItem>
            )}
          </li>
        )
      })}
    </ul>
  )
}
