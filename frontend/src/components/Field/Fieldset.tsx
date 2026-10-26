import { useId, type ReactNode } from 'react'
import { copy } from '../../copy'
import styles from './Field.module.css'

type Props = { legend: string; hint?: string; error?: string | undefined; children: ReactNode }

/** A group of related inputs (times, days) with one legend, hint and error, laid out like TextField. */
export function Fieldset({ legend, hint, error, children }: Props) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = [hint === undefined ? null : hintId, error === undefined ? null : errorId]
    .filter((part) => part !== null)
    .join(' ')

  return (
    <fieldset
      aria-describedby={describedBy === '' ? undefined : describedBy}
      className={`${styles.fieldset} ${error === undefined ? '' : (styles.invalid ?? '')}`}
    >
      <legend className={styles.label}>{legend}</legend>
      {hint === undefined ? null : (
        <p id={hintId} className={styles.hint}>
          {hint}
        </p>
      )}
      {error === undefined ? null : (
        <p id={errorId} className={styles.error}>
          <span className="visually-hidden">{copy.form.errorPrefix}</span> {error}
        </p>
      )}
      {children}
    </fieldset>
  )
}
