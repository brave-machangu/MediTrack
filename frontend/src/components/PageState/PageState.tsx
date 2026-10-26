import type { ReactNode } from 'react'
import { ApiError } from '../../api/client'
import { errorMessage } from '../../api/errors'
import { copy } from '../../copy'
import { Button } from '../Button/Button'
import { Notice } from '../Notice/Notice'
import styles from './PageState.module.css'

/** Calm text plus static placeholders shaped like the content. No spinner, no shimmer. */
export function LoadingState({ label }: { label: string }) {
  return (
    <div className={styles.loading}>
      <p role="status">{label}</p>
      <div className={styles.placeholder} aria-hidden="true" />
      <div className={styles.placeholder} aria-hidden="true" />
    </div>
  )
}

/** Says what is empty and what to do about it. */
export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className={styles.empty}>
      <h2>{title}</h2>
      <p>{body}</p>
      {action}
    </div>
  )
}

type ErrorProps = { title: string; error: unknown; onRetry: () => void; retrying: boolean }

/** Nothing could be loaded. Retry stays enabled (a repeat press is harmless), so focus isn't lost while it runs. */
export function ErrorState({ title, error, onRetry, retrying }: ErrorProps) {
  const traceId = error instanceof ApiError ? error.traceId : undefined
  return (
    <Notice tone="error">
      <h2>{title}</h2>
      <p>{errorMessage(error)}</p>
      {traceId === undefined ? null : <p>{copy.error.supportReference(traceId)}</p>}
      <Button variant="primary" onClick={onRetry}>
        {retrying ? copy.action.retrying : copy.action.retry}
      </Button>
    </Notice>
  )
}
