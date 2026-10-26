import { Plus } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTodayDoses } from '../../api/doses'
import { useMedications, useStopMedication } from '../../api/medications'
import { usePatient, usePatientId } from '../../api/patients'
import { Button } from '../../components/Button/Button'
import { ConfirmDialog } from '../../components/ConfirmDialog/ConfirmDialog'
import { Notice } from '../../components/Notice/Notice'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { EmptyState, ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { MedicationForm } from './MedicationForm'
import { MedicationList } from './MedicationList'
import styles from './medications.module.css'
import { useOpenForm, type OpenForm } from './useOpenForm'

export function MedicationsPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const medications = useMedications(patientId)
  // The patient's today, from the server: dates show a year only when it isn't this one (DD-6, DD-7).
  const today = useTodayDoses(patientId).data
  const stop = useStopMedication(patientId)
  // Destructured: the hook hands out ref callbacks, and the React lint treats a whole object passed that way as a ref.
  const { open, saved, focusSaved, focusIf, openForm: setOpenForm, cancel, onSaved } = useOpenForm()
  const [showStopped, setShowStopped] = useState(false)

  const openForm = (form: OpenForm) => {
    stop.reset()
    setOpenForm(form)
  }

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
  } else {
    const all = medications.data
    const stopping = open?.kind === 'stop' ? all.find((medication) => medication.id === open.id) : undefined
    content = (
      <>
        {saved === null ? null : (
          <div key={saved.count} ref={focusSaved} tabIndex={-1}>
            <Notice tone="success">
              <p>{saved.message}</p>
            </Notice>
          </div>
        )}
        {open?.kind === 'add' ? (
          <MedicationForm patientId={patientId} onSaved={onSaved} onCancel={cancel('add')} />
        ) : (
          <Button
            ref={focusIf('add')}
            className={styles.itemAction}
            onClick={() => {
              openForm({ kind: 'add' })
            }}
          >
            <Plus aria-hidden="true" />
            {copy.meds.add}
          </Button>
        )}
        {all.length === 0 && open === null ? <EmptyState title={copy.meds.empty.title} body={copy.meds.empty.body} /> : null}
        {all.some((medication) => !medication.active) ? (
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
        <MedicationList
          medications={all.filter((medication) => showStopped || medication.active)}
          patientId={patientId}
          open={open}
          focusIf={focusIf}
          cancel={cancel}
          onSaved={onSaved}
          openForm={openForm}
          timeZone={today?.timezone ?? patient.data?.timezone}
          currentYear={today?.date.slice(0, 4)}
        />
        {stopping === undefined ? null : (
          <ConfirmDialog
            title={copy.stopConfirm.title(stopping.name)}
            body={copy.stopConfirm.body}
            confirmLabel={copy.stopConfirm.confirm}
            busy={stop.isPending}
            error={stop.error}
            onConfirm={() => {
              stop.mutate(stopping.id, {
                onSuccess: () => {
                  onSaved(copy.meds.stopped(stopping.name))
                },
              })
            }}
            onCancel={cancel(`stop-${stopping.id}`)}
          />
        )}
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
