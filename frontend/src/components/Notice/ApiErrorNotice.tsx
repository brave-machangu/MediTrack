import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'
import { copy } from '../../copy'
import { Notice } from './Notice'
import styles from './Notice.module.css'

type Props = {
  error: unknown
  focusRef?: ((element: HTMLElement | null) => void) | undefined
  /** For example "Not recorded." when a dose may not have been saved. */
  prefix?: string
}

/** A failed request explained in plain words, with the support reference when the server sent one. */
export function ApiErrorNotice({ error, focusRef, prefix }: Props) {
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
