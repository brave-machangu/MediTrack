import type { ReactNode } from 'react'
import { isLogWindowOpen, type DoseLog, type PlannedDose } from '../../api/doses'
import { copy } from '../../copy'
import { formatTime } from '../../dates'
import { Button } from '../Button/Button'
import { ApiErrorNotice } from '../Notice/ApiErrorNotice'
import { Notice } from '../Notice/Notice'
import styles from './DoseCard.module.css'
import { isDuplicate, isRetryable, useDoseActions } from './useDoseActions'

type Props = {
  dose: PlannedDose
  patientId: string
  timeZone: string
  at: Date
  focusHeading: () => void
  onRecordChange: ((log: DoseLog | null) => void) | undefined
}

/** Taken / Skipped, the result with Undo, and every failure for one dose. Shows only what the server confirmed. */
export function DoseActions({ dose, patientId, timeZone, at, focusHeading, onRecordChange }: Props) {
  const actions = useDoseActions(dose, patientId, focusHeading, onRecordChange)
  const { record, undo, focusIf } = actions
  const context = <span className="visually-hidden">{copy.dose.context(dose.medication_name, dose.local_time)}</span>
  const windowOpen = isLogWindowOpen(dose, at)

  // 409: the server already has a record. It sits first in every branch, so React keeps the same element
  // while the refetched day arrives, instead of flashing an error.
  const alreadyRecorded = isDuplicate(record.error) ? (
    <Notice tone="info">
      <p>{copy.error.DUPLICATE_DOSE_LOG}</p>
    </Notice>
  ) : null
  // An undo stays "Undoing…" until the refetched day replaces this view.
  const undoing = undo.isPending || undo.isSuccess

  let body: ReactNode = null
  if ((dose.status === 'taken' || dose.status === 'skipped') && dose.dose_log_id) {
    const time = dose.recorded_at ? formatTime(dose.recorded_at, timeZone) : ''
    body = (
      <>
        {alreadyRecorded}
        {/* Keys stop React from reusing the Skipped button's element as Undo (and animating between them). */}
        <div key="result" className={styles.result}>
          <p ref={focusIf('result')} tabIndex={-1}>
            {dose.status === 'taken' ? copy.dose.recordedTaken(time) : copy.dose.recordedSkipped(time)}
          </p>
          {windowOpen ? (
            <Button variant="quiet" disabled={undoing} onClick={actions.undoRecord}>
              {undoing ? copy.dose.undoing : copy.dose.undo}
              {context}
            </Button>
          ) : null}
        </div>
        {/* DD-2: undoing now would leave a missed dose that could never be recorded again. */}
        {windowOpen ? null : <p className={styles.note}>{copy.dose.undoClosed}</p>}
        {undo.isError ? <ApiErrorNotice error={undo.error} focusRef={focusIf('error')} /> : null}
      </>
    )
  } else if (alreadyRecorded !== null) {
    // Same shape as the branch above (a fragment starting with the notice), so the notice isn't remounted.
    body = <>{alreadyRecorded}</>
  } else if (record.isError && isRetryable(record.error)) {
    body = (
      <>
        <ApiErrorNotice error={record.error} focusRef={focusIf('error')} prefix={copy.dose.notRecorded} />
        <div key="retry" className={styles.buttons}>
          <Button variant="primary" className={styles.doseButton} onClick={actions.retry}>
            {copy.action.retry}
            {context}
          </Button>
          <Button className={styles.doseButton} onClick={actions.cancel}>
            {copy.action.cancel}
          </Button>
        </div>
      </>
    )
  } else if (windowOpen) {
    const saving = record.isPending ? record.variables.status : undefined
    body = (
      <>
        {record.isError ? <ApiErrorNotice error={record.error} focusRef={focusIf('error')} /> : null}
        <div key="record" className={styles.buttons}>
          <Button
            ref={focusIf('taken')}
            variant="primary"
            className={styles.doseButton}
            disabled={record.isPending}
            onClick={actions.markTaken}
          >
            {saving === 'taken' ? copy.action.saving : copy.dose.taken}
            {context}
          </Button>
          <Button className={styles.doseButton} disabled={record.isPending} onClick={actions.markSkipped}>
            {saving === 'skipped' ? copy.action.saving : copy.dose.skipped}
            {context}
          </Button>
        </div>
      </>
    )
  }

  if (body === null) return null
  return (
    <div className={styles.actions}>
      {/* Always rendered, so screen readers hear the change when an undo succeeds. */}
      <p role="status" className="visually-hidden">
        {actions.undone ? copy.dose.undone : ''}
      </p>
      {body}
    </div>
  )
}
