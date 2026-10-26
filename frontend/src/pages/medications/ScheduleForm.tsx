import { useId, useState, type SubmitEvent } from 'react'
import { useSaveSchedule, type Medication, type Schedule } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { ErrorSummary, type SummaryItem } from '../../components/Field/ErrorSummary'
import fieldStyles from '../../components/Field/Field.module.css'
import { TextField } from '../../components/Field/TextField'
import { ApiErrorNotice } from '../../components/Notice/ApiErrorNotice'
import { copy } from '../../copy'
import styles from './medications.module.css'
import { DaysFieldset, dayFieldId, TimesFieldset, timeFieldId } from './ScheduleFields'
import {
  hasErrors,
  scheduleValues,
  serverScheduleErrors,
  toScheduleBody,
  validateSchedule,
  type ScheduleErrors,
  type ScheduleValues,
} from './scheduleValues'

type Props = {
  patientId: string
  medication: Medication
  /** The schedule to edit (it has no recorded doses); without it, the form adds one. */
  schedule?: Schedule
  /** The patient's today, the default start for a new schedule. */
  defaultStart: string
  onSaved: (message: string) => void
  onCancel: () => void
}

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/** Add a schedule, or edit one with no recorded doses (DESIGN.md §6.6, AC-05, AC-34). */
export function ScheduleForm({ patientId, medication, schedule, defaultStart, onSaved, onCancel }: Props) {
  const id = useId()
  const [values, setValues] = useState(() => scheduleValues(schedule, defaultStart))
  const [errors, setErrors] = useState<ScheduleErrors>({})
  const [summary, setSummary] = useState<{ attempt: number; items: SummaryItem[] } | null>(null)
  const save = useSaveSchedule(patientId, schedule === undefined ? { medicationId: medication.id } : { scheduleId: schedule.id })
  const fieldId = { start: `${id}-start`, end: `${id}-end`, grace: `${id}-grace` }

  function showErrors(found: ScheduleErrors) {
    setErrors(found)
    const items: SummaryItem[] = [
      ...Object.entries(found.times ?? {}).map(([index, message = '']) => ({
        message,
        fieldId: timeFieldId(id, Number(index)),
      })),
      ...(found.days === undefined ? [] : [{ message: found.days, fieldId: dayFieldId(id, 1) }]),
      ...(['start', 'end', 'grace'] as const).flatMap((field) => {
        const message = found[field]
        return message === undefined ? [] : [{ message, fieldId: fieldId[field] }]
      }),
      ...(found.other ?? []).map((message) => ({ message })),
    ]
    setSummary((previous) => ({ attempt: (previous?.attempt ?? 0) + 1, items }))
  }

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = validateSchedule(values)
    if (hasErrors(found)) {
      showErrors(found)
      return
    }
    setErrors({})
    setSummary(null)
    save.mutate(toScheduleBody(values), {
      onSuccess: () => {
        onSaved(schedule === undefined ? copy.scheduleForm.added : copy.scheduleForm.saved)
      },
      onError: (error) => {
        const server = serverScheduleErrors(error)
        if (server !== null) showErrors(hasErrors(server) ? server : { other: [copy.error.VALIDATION_ERROR] })
      },
    })
  }

  const set = <K extends keyof ScheduleValues>(field: K, value: ScheduleValues[K]) => {
    setValues((previous) => ({ ...previous, [field]: value }))
  }
  const headingId = `${id}-heading`
  // Overlap (AC-34) and other refusals: shown at the top of the form, taking focus after each attempt.
  const refused = save.isError && serverScheduleErrors(save.error) === null

  return (
    <form noValidate onSubmit={submit} aria-labelledby={headingId} className={styles.form}>
      <h3 id={headingId} ref={focusOnAttach} tabIndex={-1}>
        {schedule === undefined ? copy.scheduleForm.addTitle(medication.name) : copy.scheduleForm.editTitle}
      </h3>
      {summary === null ? null : <ErrorSummary key={summary.attempt} items={summary.items} />}
      {refused ? <ApiErrorNotice key={save.submittedAt} error={save.error} focusRef={focusOnAttach} /> : null}
      <TimesFieldset idPrefix={id} times={values.times} errors={errors.times} onChange={(times) => { set('times', times) }} />
      <DaysFieldset idPrefix={id} days={values.days} error={errors.days} onChange={(days) => { set('days', days) }} />
      <TextField
        id={fieldId.start}
        type="date"
        label={copy.scheduleForm.start}
        error={errors.start}
        value={values.start}
        className={fieldStyles.short}
        onChange={(event) => { set('start', event.target.value) }}
      />
      <TextField
        id={fieldId.end}
        type="date"
        label={copy.scheduleForm.end}
        hint={copy.scheduleForm.endHint}
        optional
        error={errors.end}
        value={values.end}
        className={fieldStyles.short}
        onChange={(event) => { set('end', event.target.value) }}
      />
      <TextField
        id={fieldId.grace}
        inputMode="numeric"
        label={copy.scheduleForm.grace}
        hint={copy.scheduleForm.graceHint}
        error={errors.grace}
        value={values.grace}
        className={fieldStyles.short}
        onChange={(event) => { set('grace', event.target.value) }}
      />
      <div className={styles.formActions}>
        <Button type="submit" variant="primary" disabled={save.isPending}>
          {save.isPending ? copy.action.saving : copy.scheduleForm.save}
        </Button>
        <Button onClick={onCancel}>{copy.action.cancel}</Button>
      </div>
    </form>
  )
}
