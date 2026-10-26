import type { ComponentProps } from 'react'
import { copy } from '../../copy'
import styles from './Field.module.css'

type Props = Omit<ComponentProps<'input'>, 'id'> & {
  id: string
  label: string
  hint?: string
  error?: string | undefined
  optional?: boolean
}

/**
 * A labelled input: label, hint, error, then the input (DESIGN.md §4.6). Never truncates what was typed;
 * length limits are checked on submit and explained.
 */
export function TextField({ id, label, hint, error, optional = false, className, ...input }: Props) {
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = [hint === undefined ? null : hintId, error === undefined ? null : errorId]
    .filter((part) => part !== null)
    .join(' ')

  return (
    <div className={`${styles.field} ${error === undefined ? '' : (styles.invalid ?? '')}`}>
      <label htmlFor={id} className={styles.label}>
        {optional ? `${label} ${copy.form.optional}` : label}
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
      <input
        id={id}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={describedBy === '' ? undefined : describedBy}
        className={`${styles.input} ${className ?? ''}`}
        {...input}
      />
    </div>
  )
}
