import { RotateCw } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useTodayDoses, type PlannedDose } from '../../api/doses'
import { usePatient, usePatientId } from '../../api/patients'
import { useNow } from '../../clock'
import { Button, buttonClassName } from '../../components/Button/Button'
import { Notice } from '../../components/Notice/Notice'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { EmptyState, ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { browserTimeZone, formatDate, formatTime, timeZoneLabel } from '../../dates'
import { DoseGroups } from './DoseGroups'
import styles from './today.module.css'

export function TodayPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const day = useTodayDoses(patientId)
  const refresh = useRefresh(day.refetch)
  const at = useNow()

  let content: ReactNode
  if (day.data === undefined) {
    content = day.isError ? (
      <ErrorState title={copy.today.error.title} error={day.error} onRetry={() => void day.refetch()} retrying={day.isFetching} />
    ) : (
      <LoadingState label={copy.today.loading} />
    )
  } else if (day.data.doses.length === 0) {
    const medicationsPath = `/patients/${encodeURIComponent(patientId)}/medications`
    content = (
      <EmptyState
        title={copy.today.empty.title}
        body={copy.today.empty.body}
        action={
          <Link to={medicationsPath} className={buttonClassName('primary')}>
            {copy.today.empty.action}
          </Link>
        }
      />
    )
  } else {
    const { timezone, doses } = day.data
    content = (
      <>
        <div className={styles.controls}>
          {/* A failed refetch keeps the last data on screen; Refresh below is the way to try again. */}
          {day.isError ? (
            <Notice tone="warning">
              <p>{copy.error.stale(formatTime(new Date(day.dataUpdatedAt).toISOString(), timezone))}</p>
            </Notice>
          ) : null}
          <Button onClick={refresh.run}>
            <RotateCw aria-hidden="true" />
            {refresh.running ? copy.today.refreshing : copy.today.refresh}
          </Button>
          <p role="status" className="visually-hidden">
            {refresh.announced ? copy.today.refreshed : ''}
          </p>
        </div>
        <DoseGroups key={refresh.generation} doses={doses} patientId={patientId} timeZone={timezone} at={at} />
      </>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <PageHeading
          heading={day.data ? copy.today.title(formatDate(day.data.date)) : copy.today.titleLoading}
          pageName={copy.nav.today}
          patientName={patient.data?.display_name}
        />
        {day.data ? <DaySummary doses={day.data.doses} timeZone={day.data.timezone} /> : null}
      </div>
      {content}
    </div>
  )
}

/** Refresh refetches and, if that worked, regroups the cards by remounting the list (DD-1). */
function useRefresh(refetch: () => Promise<{ isError: boolean }>) {
  const [state, setState] = useState({ generation: 0, running: false, announced: false })
  const run = () => {
    if (state.running) return
    setState((previous) => ({ ...previous, running: true, announced: false }))
    void refetch().then((result) => {
      setState((previous) => ({
        generation: result.isError ? previous.generation : previous.generation + 1,
        running: false,
        announced: !result.isError,
      }))
    })
  }
  return { ...state, run }
}

function DaySummary({ doses, timeZone }: { doses: PlannedDose[]; timeZone: string }) {
  const recorded = doses.filter((dose) => dose.status === 'taken' || dose.status === 'skipped').length
  const next = doses.find((dose) => dose.status === 'upcoming')
  return (
    <>
      {timeZone === browserTimeZone() ? null : (
        <p className={styles.note}>{copy.today.timezoneNote(timeZoneLabel(timeZone))}</p>
      )}
      {doses.length > 0 ? (
        <p>
          <span className={next ? styles.beforeNext : undefined}>{copy.today.progress(recorded, doses.length)}</span>{' '}
          {next ? <span className={styles.next}>{copy.today.next(next.local_time, next.medication_name)}</span> : null}
        </p>
      ) : null}
    </>
  )
}
