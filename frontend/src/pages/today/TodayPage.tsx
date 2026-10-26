import { useTodayDoses, type PlannedDose } from '../../api/doses'
import { usePatient, usePatientId } from '../../api/patients'
import { useNow } from '../../clock'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { copy } from '../../copy'
import { browserTimeZone, formatDate, timeZoneLabel } from '../../dates'
import { DoseGroups } from './DoseGroups'
import styles from './today.module.css'

export function TodayPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const day = useTodayDoses(patientId)
  const at = useNow()

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
      {day.data ? <DoseGroups doses={day.data.doses} timeZone={day.data.timezone} at={at} /> : null}
    </div>
  )
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
