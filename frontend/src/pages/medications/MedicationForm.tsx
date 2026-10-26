import { useId, useState, type SubmitEvent } from 'react'
import { useSaveMedication, type Medication } from '../../api/medications'
import { Button } from '../../components/Button/Button'
import { ErrorSummary, type SummaryItem } from '../../components/Field/ErrorSummary'
import { TextField } from '../../components/Field/TextField'
import { ApiErrorNotice } from '../../components/Notice/ApiErrorNotice'
import { copy } from '../../copy'
import {
  serverMedicationErrors,
  toMedicationBody,
  validateMedication,
  type MedicationErrors,
  type MedicationValues,
} from './medicationValues'
import styles from './medications.module.css'

type Props = {
  patientId: string
  /** The medication to edit; without it, the form adds one. */
  medication?: Medication
  onSaved: (message: string) => void
  onCancel: () => void
}

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/** Add or edit a medication in place on the page (DESIGN.md §4.6, DD-8). */
export function MedicationForm({ patientId, medication, onSaved, onCancel }: Props) {
  const id = useId()
  const fieldId = { name: `${id}-name`, dosage: `${id}-dosage`, instructions: `${id}-instructions` }
  const [values, setValues] = useState<MedicationValues>({
    name: medication?.name ?? '',
    dosage: medication?.dosage_label ?? '',
    instructions: medication?.instructions ?? '',
  })
  const [errors, setErrors] = useState<MedicationErrors>({})
  // A new attempt number remounts the summary, so it takes focus again after every failed submit.
  const [summary, setSummary] = useState<{ attempt: number; items: SummaryItem[] } | null>(null)
  const save = useSaveMedication(patientId, medication?.id)

  function showErrors(fields: MedicationErrors, other: string[] = []) {
    setErrors(fields)
    const items: SummaryItem[] = [
      ...(['name', 'dosage', 'instructions'] as const).flatMap((field) => {
        const message = fields[field]
        return message === undefined ? [] : [{ message, fieldId: fieldId[field] }]
      }),
      ...other.map((message) => ({ message })),
    ]
    setSummary((previous) => ({ attempt: (previous?.attempt ?? 0) + 1, items }))
  }

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const clientErrors = validateMedication(values)
    if (Object.keys(clientErrors).length > 0) {
      showErrors(clientErrors)
      return
    }
    setErrors({})
    setSummary(null)
    save.mutate(toMedicationBody(values), {
      onSuccess: (saved) => {
        onSaved(medication === undefined ? copy.medForm.added(saved.name) : copy.medForm.saved)
      },
      onError: (error) => {
        const server = serverMedicationErrors(error)
        if (server === null) return
        // The generic line only when nothing more specific came back.
        const nothingSpecific = Object.keys(server.fields).length === 0 && server.other.length === 0
        showErrors(server.fields, nothingSpecific ? [copy.error.VALIDATION_ERROR] : server.other)
      },
    })
  }

  const update = (field: keyof MedicationValues) => (event: { target: { value: string } }) => {
    setValues((previous) => ({ ...previous, [field]: event.target.value }))
  }
  const headingId = `${id}-heading`

  return (
    <form noValidate onSubmit={submit} aria-labelledby={headingId} className={styles.form}>
      <h2 id={headingId} ref={focusOnAttach} tabIndex={-1}>
        {medication === undefined ? copy.medForm.addTitle : copy.medForm.editTitle(medication.name)}
      </h2>
      {summary === null ? null : <ErrorSummary key={summary.attempt} items={summary.items} />}
      {save.isError && serverMedicationErrors(save.error) === null ? <ApiErrorNotice error={save.error} /> : null}
      <TextField
        id={fieldId.name}
        label={copy.medForm.name}
        hint={copy.medForm.nameHint}
        error={errors.name}
        value={values.name}
        onChange={update('name')}
        autoComplete="off"
      />
      <TextField
        id={fieldId.dosage}
        label={copy.medForm.dosage}
        hint={copy.medForm.dosageHint}
        error={errors.dosage}
        value={values.dosage}
        onChange={update('dosage')}
        autoComplete="off"
      />
      <TextField
        id={fieldId.instructions}
        label={copy.medForm.instructions}
        hint={copy.medForm.instructionsHint}
        error={errors.instructions}
        value={values.instructions}
        onChange={update('instructions')}
        optional
        autoComplete="off"
      />
      <div className={styles.formActions}>
        <Button type="submit" variant="primary" disabled={save.isPending}>
          {save.isPending ? copy.action.saving : copy.medForm.save}
        </Button>
        <Button onClick={onCancel}>{copy.action.cancel}</Button>
      </div>
    </form>
  )
}
