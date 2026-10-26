import { useState, type ReactNode } from 'react'
import { ApiError } from '../../api/client'
import { useDailySummary, usePatientToday } from '../../api/doses'
import { usePatient, usePatientId } from '../../api/patients'
import { Button } from '../../components/Button/Button'
import { Notice } from '../../components/Notice/Notice'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { formatTime } from '../../dates'
import { DateForm } from './DateForm'
import { DaySummary } from './DaySummary'
import styles from './summary.module.css'

/** Counts and adherence for one patient-local date, today by default (DESIGN.md §6.8, FR-09). */
export function SummaryPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const today = usePatientToday(patientId).data
  // Undefined until a date is chosen, so the server uses the patient's today.
  const [date, setDate] = useState<string>()
  // Counts Show presses: each one remounts the result with its heading focused.
  const [shows, setShows] = useState(0)
  const summary = useDailySummary(patientId, date)
  const refused = refusal(summary.error)

  const show = (next: string) => {
    // The same date again keeps the same query, so fetch it afresh.
    if (next === date) void summary.refetch()
    setDate(next)
    setShows((previous) => previous + 1)
  }

  let content: ReactNode
  if (refused !== null) {
    // The form explains the server's refusal next to its field.
    content = null
  } else if (summary.data === undefined) {
    content = summary.isError ? (
      <ErrorState
        title={copy.summary.error.title}
        error={summary.error}
        onRetry={() => void summary.refetch()}
        retrying={summary.isFetching}
      />
    ) : (
      <LoadingState label={copy.summary.loading} />
    )
  } else {
    content = (
      <>
        {/* A failed refetch keeps the last summary on screen (DESIGN.md §4.3). */}
        {summary.isError ? (
          <Notice tone="warning">
            <p>{copy.error.stale(formatTime(new Date(summary.dataUpdatedAt).toISOString(), summary.data.timezone))}</p>
            <Button onClick={() => void summary.refetch()} disabled={summary.isFetching}>
              {copy.action.retry}
            </Button>
          </Notice>
        ) : null}
        <DaySummary key={shows} summary={summary.data} currentYear={today?.slice(0, 4)} focusHeading={shows > 0} />
      </>
    )
  }

  return (
    <div className={styles.page}>
      <PageHeading heading={copy.summary.title} pageName={copy.nav.summary} patientName={patient.data?.display_name} />
      <DateForm
        initial={date ?? today}
        serverError={refused === null ? null : { key: summary.errorUpdatedAt, message: refused }}
        onShow={show}
      />
      {content}
    </div>
  )
}

/** A 422 for the date: the server's message for `date` (the backend names it after the parameter), or the general one. */
function refusal(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.code !== 'VALIDATION_ERROR') return null
  return error.fieldErrors.find((fieldError) => fieldError.field === 'date')?.message ?? copy.error.VALIDATION_ERROR
}
