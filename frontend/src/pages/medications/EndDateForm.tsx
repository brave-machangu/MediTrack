import { useId, useState, type SubmitEvent } from 'react'
import { useEndSchedule, type Schedule } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { ErrorSummary } from '../../components/Field/ErrorSummary'
import fieldStyles from '../../components/Field/Field.module.css'
import { TextField } from '../../components/Field/TextField'
import { ApiErrorNotice } from '../../components/Notice/ApiErrorNotice'
import { copy } from '../../copy'
import styles from './medications.module.css'
import { serverScheduleErrors } from './scheduleValues'

type Props = {
  patientId: string
  schedule: Schedule
  /** The patient's today, the default when the schedule has no end date yet. */
  today: string | undefined
  onSaved: (message: string) => void
  onCancel: () => void
}

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/** "Change end date" for a schedule with records: the one change allowed (requirements §4.4, AC-06). */
export function EndDateForm({ patientId, schedule, today, onSaved, onCancel }: Props) {
  const id = useId()
  const [value, setValue] = useState(schedule.end_date ?? today ?? '')
  const [error, setError] = useState<{ attempt: number; message: string } | null>(null)
  const end = useEndSchedule(patientId, schedule.id)
  const fieldId = `${id}-end`

  const showError = (message: string) => {
    setError((previous) => ({ attempt: (previous?.attempt ?? 0) + 1, message }))
  }

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (value === '') {
      showError(copy.changeSchedule.endRequired)
      return
    }
    setError(null)
    end.mutate(value, {
      onSuccess: () => {
        onSaved(copy.endDate.saved)
      },
      onError: (failure) => {
        const server = serverScheduleErrors(failure)
        if (server !== null) showError(server.end ?? server.other?.[0] ?? copy.error.VALIDATION_ERROR)
      },
    })
  }

  const headingId = `${id}-heading`
  return (
    <form noValidate onSubmit={submit} aria-labelledby={headingId} className={styles.form}>
      <h3 id={headingId} ref={focusOnAttach} tabIndex={-1}>
        {copy.endDate.title}
      </h3>
      {error === null ? null : <ErrorSummary key={error.attempt} items={[{ message: error.message, fieldId }]} />}
      {end.isError && serverScheduleErrors(end.error) === null ? (
        <ApiErrorNotice key={end.submittedAt} error={end.error} focusRef={focusOnAttach} />
      ) : null}
      <TextField
        id={fieldId}
        type="date"
        label={copy.endDate.label}
        hint={copy.endDate.hint}
        error={error?.message}
        value={value}
        min={today}
        className={fieldStyles.short}
        onChange={(event) => {
          setValue(event.target.value)
        }}
      />
      <div className={styles.formActions}>
        <Button type="submit" variant="primary" disabled={end.isPending}>
          {end.isPending ? copy.action.saving : copy.changeSchedule.save}
        </Button>
        <Button onClick={onCancel}>{copy.action.cancel}</Button>
      </div>
    </form>
  )
}
