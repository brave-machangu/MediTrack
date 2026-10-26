import { useId, useState, type SubmitEvent } from 'react'
import type { DateRange } from '../../api/doses'
import { Button } from '../../components/Button/Button'
import { ErrorSummary, type SummaryItem } from '../../components/Field/ErrorSummary'
import fieldStyles from '../../components/Field/Field.module.css'
import { Fieldset } from '../../components/Field/Fieldset'
import { TextField } from '../../components/Field/TextField'
import { copy } from '../../copy'
import { rangeErrors, type RangeErrors } from './range'
import styles from './missed.module.css'

type Props = {
  /** The range on screen, once the patient's today is known. A field shows it until someone changes that field. */
  initial: DateRange | undefined
  /** The server's refusal of the last range shown, with a key that changes on each refusal. */
  serverErrors: { key: number; errors: RangeErrors } | null
  onShow: (range: DateRange) => void
}

/** "Dates" with From and To (DESIGN.md §6.7). The server isn't asked until both dates pass its rules. */
export function RangeForm({ initial, serverErrors, onShow }: Props) {
  const id = useId()
  // Only what was typed, so a field nobody touched still fills in when the patient's today arrives late.
  const [typed, setTyped] = useState<Partial<DateRange>>({})
  const values: DateRange = { from: typed.from ?? initial?.from ?? '', to: typed.to ?? initial?.to ?? '' }
  const [checked, setChecked] = useState<{ attempt: number; errors: RangeErrors } | null>(null)
  const errors = checked?.errors ?? serverErrors?.errors ?? {}
  const fromId = `${id}-from`
  const toId = `${id}-to`

  const summaryItems: SummaryItem[] = [
    ...(errors.range === undefined ? [] : [{ message: errors.range, fieldId: fromId }]),
    ...(errors.from === undefined ? [] : [{ message: errors.from, fieldId: fromId }]),
    ...(errors.to === undefined ? [] : [{ message: errors.to, fieldId: toId }]),
    ...(errors.other ?? []).map((message) => ({ message })),
  ]
  const summaryKey = checked === null ? `server-${String(serverErrors?.key)}` : `checked-${String(checked.attempt)}`

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = rangeErrors(values)
    if (Object.keys(found).length > 0) {
      setChecked((previous) => ({ attempt: (previous?.attempt ?? 0) + 1, errors: found }))
      return
    }
    setChecked(null)
    onShow(values)
  }

  return (
    <form noValidate onSubmit={submit} className={styles.form}>
      {summaryItems.length === 0 ? null : <ErrorSummary key={summaryKey} items={summaryItems} />}
      <Fieldset legend={copy.missed.range} hint={copy.missed.rangeHint} error={errors.range}>
        <TextField
          id={fromId}
          type="date"
          label={copy.missed.from}
          error={errors.from}
          value={values.from}
          className={fieldStyles.short}
          onChange={(event) => {
            setTyped({ ...typed, from: event.target.value })
          }}
        />
        <TextField
          id={toId}
          type="date"
          label={copy.missed.to}
          error={errors.to}
          value={values.to}
          className={fieldStyles.short}
          onChange={(event) => {
            setTyped({ ...typed, to: event.target.value })
          }}
        />
      </Fieldset>
      <div>
        <Button type="submit">{copy.missed.show}</Button>
      </div>
    </form>
  )
}
