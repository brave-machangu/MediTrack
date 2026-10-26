import { useId, useState, type SubmitEvent } from 'react'
import { Button } from '../../components/Button/Button'
import { ErrorSummary } from '../../components/Field/ErrorSummary'
import fieldStyles from '../../components/Field/Field.module.css'
import { TextField } from '../../components/Field/TextField'
import { copy } from '../../copy'
import styles from './summary.module.css'

type Props = {
  /** The date on screen, or the patient's today once known. The field shows it until someone changes it. */
  initial: string | undefined
  /** The server's refusal of the last date shown, with a key that changes on each refusal. */
  serverError: { key: number; message: string } | null
  onShow: (date: string) => void
}

/** "Date" and Show summary (DESIGN.md §6.8). An empty date is explained before anything is sent. */
export function DateForm({ initial, serverError, onShow }: Props) {
  const id = useId()
  // Only what was typed, so an untouched field still fills in when the patient's today arrives late.
  const [typed, setTyped] = useState<string>()
  const value = typed ?? initial ?? ''
  const [attempt, setAttempt] = useState<number | null>(null)
  const error = attempt === null ? serverError?.message : copy.summary.dateRequired
  const fieldId = `${id}-date`

  function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (value === '') {
      setAttempt((previous) => (previous ?? 0) + 1)
      return
    }
    setAttempt(null)
    onShow(value)
  }

  return (
    <form noValidate onSubmit={submit} className={styles.form}>
      {error === undefined ? null : (
        <ErrorSummary
          key={attempt === null ? `server-${String(serverError?.key)}` : `checked-${String(attempt)}`}
          items={[{ message: error, fieldId }]}
        />
      )}
      <TextField
        id={fieldId}
        type="date"
        label={copy.summary.date}
        error={error}
        value={value}
        className={fieldStyles.short}
        onChange={(event) => {
          setTyped(event.target.value)
        }}
      />
      <div>
        <Button type="submit">{copy.summary.show}</Button>
      </div>
    </form>
  )
}
