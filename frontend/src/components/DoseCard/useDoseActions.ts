import { useRef, useState } from 'react'
import { ApiError } from '../../api/client'
import { useRecordDose, useUndoDose, type DoseLogCreate, type PlannedDose } from '../../api/doses'

type FocusTarget = 'result' | 'error' | 'taken' | null

/** Focus follows the person's action to the element that now answers it (DESIGN.md §4.2, DD-10). */
const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

export const isDuplicate = (error: unknown) => error instanceof ApiError && error.code === 'DUPLICATE_DOSE_LOG'

/** No answer, or the server failed: the record may not exist, so offer Retry (AC-36). */
export const isRetryable = (error: unknown) =>
  error instanceof ApiError && (error.kind !== 'problem' || (error.status ?? 500) >= 500)

/** State and handlers behind DoseActions: one record or undo at a time, and where focus goes afterwards. */
export function useDoseActions(dose: PlannedDose, patientId: string, focusHeading: () => void) {
  const record = useRecordDose(patientId)
  const undo = useUndoDose(patientId)
  // Stops a double tap that lands before React re-renders the disabled buttons (AC-21).
  const inFlight = useRef(false)
  const [focusTarget, setFocusTarget] = useState<FocusTarget>(null)
  const [undone, setUndone] = useState(false)

  function send(status: DoseLogCreate['status']) {
    if (inFlight.current) return
    inFlight.current = true
    setFocusTarget(null)
    setUndone(false)
    undo.reset()
    record.mutate(
      { schedule_id: dose.schedule_id, scheduled_for: dose.scheduled_for, status },
      {
        onSuccess: () => {
          setFocusTarget('result')
        },
        onError: (error) => {
          setFocusTarget(isDuplicate(error) ? 'result' : 'error')
        },
        onSettled: () => {
          inFlight.current = false
        },
      },
    )
  }

  function undoRecord() {
    const doseLogId = dose.dose_log_id
    if (inFlight.current || !doseLogId) return
    inFlight.current = true
    setFocusTarget(null)
    record.reset()
    undo.mutate(doseLogId, {
      onSuccess: () => {
        setUndone(true)
        focusHeading()
      },
      onError: () => {
        setFocusTarget('error')
      },
      onSettled: () => {
        inFlight.current = false
      },
    })
  }

  return {
    record,
    undo,
    undone,
    focusIf: (target: FocusTarget) => (focusTarget === target ? focusOnAttach : undefined),
    markTaken: () => {
      send('taken')
    },
    markSkipped: () => {
      send('skipped')
    },
    retry: () => {
      if (record.variables) send(record.variables.status)
    },
    cancel: () => {
      record.reset()
      setFocusTarget('taken')
    },
    undoRecord,
  }
}
