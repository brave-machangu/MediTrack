import { useState, type ReactNode } from 'react'
import { useTodayDoses } from '../../api/doses'
import { useMedications } from '../../api/medications'
import { usePatient, usePatientId } from '../../api/patients'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { EmptyState, ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { MedicationItem } from './MedicationItem'
import styles from './medications.module.css'

export function MedicationsPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const medications = useMedications(patientId)
  // The patient's today, from the server: dates show a year only when it isn't this one (DD-6, DD-7).
  const today = useTodayDoses(patientId).data
  const [showStopped, setShowStopped] = useState(false)

  let content: ReactNode
  if (medications.data === undefined) {
    content = medications.isError ? (
      <ErrorState
        title={copy.meds.error.title}
        error={medications.error}
        onRetry={() => void medications.refetch()}
        retrying={medications.isFetching}
      />
    ) : (
      <LoadingState label={copy.meds.loading} />
    )
  } else if (medications.data.length === 0) {
    content = <EmptyState title={copy.meds.empty.title} body={copy.meds.empty.body} />
  } else {
    const hasStopped = medications.data.some((medication) => !medication.active)
    const shown = medications.data.filter((medication) => showStopped || medication.active)
    content = (
      <>
        {hasStopped ? (
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={showStopped}
              onChange={(event) => {
                setShowStopped(event.target.checked)
              }}
            />
            {copy.meds.showStopped}
          </label>
        ) : null}
        {/* role="list" because Safari drops list semantics when list-style is none. */}
        <ul role="list" className={styles.list}>
          {shown.map((medication) => (
            <li key={medication.id}>
              <MedicationItem
                medication={medication}
                timeZone={today?.timezone ?? patient.data?.timezone}
                currentYear={today?.date.slice(0, 4)}
              />
            </li>
          ))}
        </ul>
      </>
    )
  }

  return (
    <div className={styles.page}>
      <PageHeading heading={copy.meds.title} pageName={copy.nav.medications} patientName={patient.data?.display_name} />
      {content}
    </div>
  )
}
