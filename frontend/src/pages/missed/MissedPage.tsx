import { useState, type ReactNode } from 'react'
import { useMissedDoses, usePatientToday, type DateRange } from '../../api/doses'
import { usePatient, usePatientId } from '../../api/patients'
import { useNow } from '../../clock'
import { Button } from '../../components/Button/Button'
import { Disclaimer } from '../../components/Disclaimer/Disclaimer'
import { Notice } from '../../components/Notice/Notice'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { formatShortDate, formatTime } from '../../dates'
import { MissedList } from './MissedList'
import styles from './missed.module.css'
import { lastSevenDays, sameRange, serverRangeErrors } from './range'
import { RangeForm } from './RangeForm'

/**
 * Missed doses for up to 31 days, the last 7 by default (DESIGN.md §6.7). Each card says only that no dose
 * was recorded (AC-38).
 */
export function MissedPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const today = usePatientToday(patientId).data
  // Undefined until dates are chosen, so the server covers the patient's last 7 days (AC-22).
  const [range, setRange] = useState<DateRange>()
  // Changes on every Show, so the list regroups and drops cards recorded since (DD-13).
  const [generation, setGeneration] = useState(0)
  const missed = useMissedDoses(patientId, range)
  const at = useNow()
  const timeZone = patient.data?.timezone
  const shown = range ?? (today === undefined ? undefined : lastSevenDays(today))
  const refused = serverRangeErrors(missed.error)

  const show = (next: DateRange) => {
    // The same dates again keep the same query, so fetch them afresh.
    if (range !== undefined && sameRange(range, next)) void missed.refetch()
    setRange(next)
    setGeneration((previous) => previous + 1)
  }

  let content: ReactNode
  if (refused !== null) {
    // The form explains the server's refusal next to its fields.
    content = null
  } else if (missed.data === undefined || timeZone === undefined) {
    content = missed.isError ? (
      <ErrorState
        title={copy.missed.error.title}
        error={missed.error}
        onRetry={() => void missed.refetch()}
        retrying={missed.isFetching}
      />
    ) : (
      <LoadingState label={copy.missed.loading} />
    )
  } else {
    content = (
      <>
        {/* A failed refetch keeps the last list on screen (DESIGN.md §4.3). */}
        {missed.isError ? (
          <Notice tone="warning">
            <p>{copy.error.stale(formatTime(new Date(missed.dataUpdatedAt).toISOString(), timeZone))}</p>
            <Button onClick={() => void missed.refetch()} disabled={missed.isFetching}>
              {copy.action.retry}
            </Button>
          </Notice>
        ) : null}
        <p role="status">{countLine(missed.data.length, shown, today)}</p>
        {/* Stays mounted when the list empties, so cards recorded here keep their place. */}
        <MissedList
          key={generation}
          doses={missed.data}
          patientId={patientId}
          timeZone={timeZone}
          at={at}
          currentYear={today?.slice(0, 4)}
        />
      </>
    )
  }

  return (
    <div className={styles.page}>
      <PageHeading heading={copy.missed.title} pageName={copy.nav.missed} patientName={patient.data?.display_name} />
      <Disclaimer inset />
      {/* Remounted when the patient's today arrives, so the dates fill in. */}
      <RangeForm
        key={today ?? 'today-loading'}
        initial={shown}
        serverErrors={refused === null ? null : { key: missed.errorUpdatedAt, errors: refused }}
        onShow={show}
      />
      {content}
    </div>
  )
}

/** "4 missed doses from 20 October to 26 October.", or "…in the last 7 days" before the patient's today is known (DD-7). */
function countLine(count: number, shown: DateRange | undefined, today: string | undefined): string {
  if (shown === undefined) return count === 0 ? copy.missed.emptyDefault : copy.missed.countDefault(count)
  const year = today?.slice(0, 4)
  const from = formatShortDate(shown.from, year)
  const to = formatShortDate(shown.to, year)
  return count === 0 ? copy.missed.empty(from, to) : copy.missed.count(count, from, to)
}
