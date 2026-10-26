import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'
import { copy } from '../../copy'
import { Notice } from '../Notice/Notice'
import styles from './DoseCard.module.css'

type Props = {
  error: unknown
  focusRef: ((element: HTMLElement | null) => void) | undefined
  /** "Not recorded." when the dose may not have been saved. */
  prefix?: string
}

/** A failed record or undo on a dose card, with the support reference when the server sent one. */
export function DoseFailure({ error, focusRef, prefix }: Props) {
  const traceId = error instanceof ApiError ? error.traceId : undefined
  return (
    <Notice tone="error">
      <p ref={focusRef} tabIndex={-1}>
        {prefix === undefined ? errorMessage(error) : `${prefix} ${errorMessage(error)}`}
      </p>
      {traceId === undefined ? null : <p className={styles.reference}>{copy.error.supportReference(traceId)}</p>}
    </Notice>
  )
}
