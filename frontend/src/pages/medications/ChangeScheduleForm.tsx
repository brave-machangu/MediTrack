import { useId, type SubmitEvent } from 'react'
import type { Medication, Schedule } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { ErrorSummary, type SummaryItem } from '../../components/Field/ErrorSummary'
import fieldStyles from '../../components/Field/Field.module.css'
import { Fieldset } from '../../components/Field/Fieldset'
import { TextField } from '../../components/Field/TextField'
import { ApiErrorNotice } from '../../components/Notice/ApiErrorNotice'
import { Notice } from '../../components/Notice/Notice'
import { copy } from '../../copy'
import { addDays, formatShortDate } from '../../dates'
import styles from './medications.module.css'
import { DaysFieldset, dayFieldId, TimesFieldset, timeFieldId } from './ScheduleFields'
import { useChangeSchedule, type ChangeErrors } from './useChangeSchedule'

type Props = {
  patientId: string
  medication: Medication
  schedule: Schedule
  today: string | undefined
  currentYear: string | undefined
  onSaved: (message: string) => void
  onCancel: () => void
}

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/** "Change schedule" for a schedule with records: it ends, and a new one starts the next day (DESIGN.md §6.6). */
export function ChangeScheduleForm({ patientId, medication, schedule, today, currentYear, onSaved, onCancel }: Props) {
  const id = useId()
  const fieldId = { ends: `${id}-ends`, start: `${id}-start`, end: `${id}-end`, grace: `${id}-grace` }
  const summaryItems = (found: ChangeErrors): SummaryItem[] => [
    ...(found.ends === undefined ? [] : [{ message: found.ends, fieldId: fieldId.ends }]),
    ...Object.entries(found.times ?? {}).map(([index, message = '']) => ({ message, fieldId: timeFieldId(id, Number(index)) })),
    ...(found.days === undefined ? [] : [{ message: found.days, fieldId: dayFieldId(id, 1) }]),
    ...(['start', 'end', 'grace'] as const).flatMap((field) => {
      const message = found[field]
      return message === undefined ? [] : [{ message, fieldId: fieldId[field] }]
    }),
    ...(found.other ?? []).map((message) => ({ message })),
  ]
  const change = useChangeSchedule({ patientId, medication, schedule, today, currentYear, summaryItems, onSaved })
  const { next, errors } = change
  const startsTomorrow = today !== undefined && next.start === addDays(today, 1)
  const headingId = `${id}-heading`

  return (
    <form
      noValidate
      onSubmit={(event: SubmitEvent<HTMLFormElement>) => {
        event.preventDefault()
        change.submit()
      }}
      aria-labelledby={headingId}
      className={styles.form}
    >
      <h3 id={headingId} ref={focusOnAttach} tabIndex={-1}>
        {copy.changeSchedule.title}
      </h3>
      <Notice tone="info">
        <p>
          {startsTomorrow || next.start === ''
            ? copy.changeSchedule.startsTomorrow
            : copy.changeSchedule.startsOn(formatShortDate(next.start, currentYear))}
        </p>
        <p>{copy.changeSchedule.explain}</p>
      </Notice>
      {change.summary === null ? null : <ErrorSummary key={change.summary.attempt} items={change.summary.items} />}
      {change.refusal === null ? null : (
        <ApiErrorNotice
          key={change.refusalKey}
          error={change.refusal}
          focusRef={focusOnAttach}
          // The current schedule has ended but the new one wasn't saved: say exactly that (DESIGN.md §7.6).
          {...(change.endedOn === null
            ? {}
            : { prefix: copy.changeSchedule.partial(formatShortDate(change.endedOn, currentYear)) })}
        />
      )}
      <TextField
        id={fieldId.ends}
        type="date"
        label={copy.changeSchedule.endsOn}
        error={errors.ends}
        value={change.ends}
        min={today}
        readOnly={change.endedOn !== null}
        className={fieldStyles.short}
        onChange={(event) => {
          change.setEnds(event.target.value)
        }}
      />
      <Fieldset legend={copy.changeSchedule.newSchedule} className={styles.group}>
        <TextField
          id={fieldId.start}
          type="date"
          label={copy.changeSchedule.startsOnLabel}
          error={errors.start}
          value={next.start}
          className={fieldStyles.short}
          onChange={(event) => {
            change.setNext('start', event.target.value)
          }}
        />
        <TimesFieldset idPrefix={id} times={next.times} errors={errors.times} onChange={(times) => { change.setNext('times', times) }} />
        <DaysFieldset idPrefix={id} days={next.days} error={errors.days} onChange={(days) => { change.setNext('days', days) }} />
        <TextField
          id={fieldId.end}
          type="date"
          label={copy.scheduleForm.end}
          hint={copy.scheduleForm.endHint}
          optional
          error={errors.end}
          value={next.end}
          className={fieldStyles.short}
          onChange={(event) => {
            change.setNext('end', event.target.value)
          }}
        />
        <TextField
          id={fieldId.grace}
          inputMode="numeric"
          label={copy.scheduleForm.grace}
          hint={copy.scheduleForm.graceHint}
          error={errors.grace}
          value={next.grace}
          className={fieldStyles.short}
          onChange={(event) => {
            change.setNext('grace', event.target.value)
          }}
        />
      </Fieldset>
      <div className={styles.formActions}>
        <Button type="submit" variant="primary" disabled={change.busy}>
          {change.busy ? copy.action.saving : change.endedOn === null ? copy.changeSchedule.save : copy.action.retry}
        </Button>
        <Button onClick={onCancel}>{copy.action.cancel}</Button>
      </div>
    </form>
  )
}
