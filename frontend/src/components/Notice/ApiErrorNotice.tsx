import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'
import { copy } from '../../copy'
import { Notice } from './Notice'

type Props = {
  error: unknown
  focusRef?: ((element: HTMLElement | null) => void) | undefined
  /** For example "Not recorded." when a dose may not have been saved. */
  prefix?: string
}

/**
 * A failed request explained in plain words. The support reference is shown for unexpected failures (5xx)
 * only; a refusal such as an overlapping schedule is explained well enough for the person to act on.
 */
export function ApiErrorNotice({ error, focusRef, prefix }: Props) {
  const unexpected = error instanceof ApiError && (error.status === undefined || error.status >= 500)
  const traceId = unexpected ? error.traceId : undefined
  return (
    <Notice tone="error">
      <p ref={focusRef} tabIndex={-1}>
        {prefix === undefined ? errorMessage(error) : `${prefix} ${errorMessage(error)}`}
      </p>
      {traceId === undefined ? null : <p>{copy.error.supportReference(traceId)}</p>}
    </Notice>
  )
}
