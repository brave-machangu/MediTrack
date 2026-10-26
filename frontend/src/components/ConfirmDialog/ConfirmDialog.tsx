import { useEffect, useId, useRef } from 'react'
import { copy } from '../../copy'
import { Button } from '../Button/Button'
import { ApiErrorNotice } from '../Notice/ApiErrorNotice'
import styles from './ConfirmDialog.module.css'

type Props = {
  /** Names the thing, e.g. "Stop Demo Med Alpha?" */
  title: string
  /** Names exactly what will happen. */
  body: string
  confirmLabel: string
  busy: boolean
  error: unknown
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Confirms a destructive action (DESIGN.md §5): only Stop medication and Delete schedule use it. A native
 * modal <dialog>: the browser traps focus, closes it on Esc and hides the page behind it.
 */
export function ConfirmDialog({ title, body, confirmLabel, busy, error, onConfirm, onCancel }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const titleId = useId()
  const bodyId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    dialog?.showModal()
    // Start on the safe choice.
    cancelRef.current?.focus()
    return () => {
      dialog?.close()
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-describedby={bodyId}
      className={styles.dialog}
      onCancel={(event) => {
        // Esc: the page decides when the dialog goes, so it unmounts cleanly.
        event.preventDefault()
        onCancel()
      }}
    >
      <h2 id={titleId}>{title}</h2>
      <p id={bodyId}>{body}</p>
      {error === null ? null : <ApiErrorNotice error={error} />}
      <div className={styles.actions}>
        <Button variant="danger" disabled={busy} onClick={onConfirm}>
          {busy ? copy.action.saving : confirmLabel}
        </Button>
        <Button ref={cancelRef} onClick={onCancel}>
          {copy.action.cancel}
        </Button>
      </div>
    </dialog>
  )
}
