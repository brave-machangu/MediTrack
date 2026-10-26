import { useId, useMemo, useState, type SubmitEvent } from 'react'
import { useSavePatient, type Patient } from '../../api/patients'
import { Button } from '../../components/Button/Button'
import { ErrorSummary, type SummaryItem } from '../../components/Field/ErrorSummary'
import { SelectField } from '../../components/Field/SelectField'
import { TextField } from '../../components/Field/TextField'
import { ApiErrorNotice } from '../../components/Notice/ApiErrorNotice'
import { copy } from '../../copy'
import { browserTimeZone } from '../../dates'
import styles from './patients.module.css'
import { serverPatientErrors, toPatientBody, validatePatient, type PatientErrors, type PatientValues } from './patientValues'
import { timeZoneGroups } from './timeZones'

type Props = {
  /** The patient to edit; without it, the form adds one. */
  patient?: Patient
  onSaved: (message: string) => void
  onCancel: () => void
}

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/** Add or edit a patient in place (DESIGN.md §6.5). */
export function PatientForm({ patient, onSaved, onCancel }: Props) {
  const id = useId()
  const fieldId = { name: `${id}-name`, timezone: `${id}-timezone` }
  const groups = useMemo(() => timeZoneGroups(), [])
  const [values, setValues] = useState<PatientValues>(() => {
    // A new patient starts on the browser's timezone, only as a suggestion: the patient may live elsewhere.
    const suggested = browserTimeZone()
    const known = groups.some((group) => group.zones.some((zone) => zone.value === suggested))
    return { name: patient?.display_name ?? '', timezone: patient?.timezone ?? (known ? suggested : '') }
  })
  const [errors, setErrors] = useState<PatientErrors>({})
  const [summary, setSummary] = useState<{ attempt: number; items: SummaryItem[] } | null>(null)
  const save = useSavePatient(patient?.id)

  function showErrors(found: PatientErrors) {
    setErrors(found)
    const items: SummaryItem[] = [
      ...(['name', 'timezone'] as const).flatMap((field) => {
        const message = found[field]
        return message === undefined ? [] : [{ message, fieldId: fieldId[field] }]
      }),
      ...(found.other ?? []).map((message) => ({ message })),
    ]
    setSummary((previous) => ({ attempt: (previous?.attempt ?? 0) + 1, items }))
  }

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = validatePatient(values)
    if (Object.keys(found).length > 0) {
      showErrors(found)
      return
    }
    setErrors({})
    setSummary(null)
    save.mutate(toPatientBody(values), {
      onSuccess: (saved) => {
        onSaved(patient === undefined ? copy.patientForm.added(saved.display_name) : copy.patientForm.saved(saved.display_name))
      },
      onError: (error) => {
        const server = serverPatientErrors(error)
        if (server !== null) showErrors(Object.keys(server).length > 0 ? server : { other: [copy.error.VALIDATION_ERROR] })
      },
    })
  }

  const headingId = `${id}-heading`
  return (
    <form noValidate onSubmit={submit} aria-labelledby={headingId} className={styles.form}>
      <h2 id={headingId} ref={focusOnAttach} tabIndex={-1}>
        {patient === undefined ? copy.patientForm.addTitle : copy.patientForm.editTitle(patient.display_name)}
      </h2>
      {summary === null ? null : <ErrorSummary key={summary.attempt} items={summary.items} />}
      {save.isError && serverPatientErrors(save.error) === null ? (
        <ApiErrorNotice key={save.submittedAt} error={save.error} focusRef={focusOnAttach} />
      ) : null}
      <TextField
        id={fieldId.name}
        label={copy.patientForm.name}
        hint={copy.patientForm.nameHint}
        error={errors.name}
        value={values.name}
        autoComplete="off"
        onChange={(event) => {
          setValues((previous) => ({ ...previous, name: event.target.value }))
        }}
      />
      <SelectField
        id={fieldId.timezone}
        label={copy.patientForm.timezone}
        hint={copy.patientForm.timezoneHint}
        error={errors.timezone}
        value={values.timezone}
        onChange={(event) => {
          setValues((previous) => ({ ...previous, timezone: event.target.value }))
        }}
      >
        {values.timezone === '' ? <option value="" /> : null}
        {groups.map((group) => (
          <optgroup key={group.region} label={group.region}>
            {group.zones.map((zone) => (
              <option key={zone.value} value={zone.value}>
                {zone.label}
              </option>
            ))}
          </optgroup>
        ))}
      </SelectField>
      <div className={styles.formActions}>
        <Button type="submit" variant="primary" disabled={save.isPending}>
          {save.isPending ? copy.action.saving : copy.patientForm.save}
        </Button>
        <Button onClick={onCancel}>{copy.action.cancel}</Button>
      </div>
    </form>
  )
}
