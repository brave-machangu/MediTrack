import { useId } from 'react'
import { copy } from '../../copy'
import styles from './Field.module.css'

export type SummaryItem = { message: string; fieldId?: string | undefined }

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/**
 * "There is a problem", with a link per error that moves focus to its field. It takes focus when it
 * appears; give it a new `key` on each failed submit so it does so again.
 */
export function ErrorSummary({ items }: { items: SummaryItem[] }) {
  const headingId = useId()
  return (
    <div ref={focusOnAttach} tabIndex={-1} role="group" aria-labelledby={headingId} className={styles.summary}>
      <h3 id={headingId}>{copy.form.errorSummaryTitle}</h3>
      <ul className={styles.summaryList}>
        {items.map((item) => (
          <li key={`${item.fieldId ?? ''}:${item.message}`}>
            {item.fieldId === undefined ? (
              item.message
            ) : (
              <a
                href={`#${item.fieldId}`}
                onClick={(event) => {
                  // Focus the field itself; following the link would only scroll to it.
                  event.preventDefault()
                  if (item.fieldId !== undefined) document.getElementById(item.fieldId)?.focus()
                }}
              >
                {item.message}
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
