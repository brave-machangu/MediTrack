import type { ComponentProps } from 'react'
import { copy } from '../../copy'
import styles from './Field.module.css'

type Props = Omit<ComponentProps<'select'>, 'id'> & {
  id: string
  label: string
  hint?: string
  error?: string | undefined
}

/** A labelled native <select>: label, hint, error, then the select, like TextField (DESIGN.md §4.6). */
export function SelectField({ id, label, hint, error, className, children, ...select }: Props) {
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = [hint === undefined ? null : hintId, error === undefined ? null : errorId]
    .filter((part) => part !== null)
    .join(' ')

  return (
    <div className={`${styles.field} ${error === undefined ? '' : (styles.invalid ?? '')}`}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
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
      <select
        id={id}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={describedBy === '' ? undefined : describedBy}
        className={`${styles.input} ${className ?? ''}`}
        {...select}
      >
        {children}
      </select>
    </div>
  )
}
