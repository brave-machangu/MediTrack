import { Plus } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTodayDoses } from '../../api/doses'
import { useMedications } from '../../api/medications'
import { usePatient, usePatientId } from '../../api/patients'
import { Button } from '../../components/Button/Button'
import { Notice } from '../../components/Notice/Notice'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { EmptyState, ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { MedicationForm } from './MedicationForm'
import { MedicationItem } from './MedicationItem'
import styles from './medications.module.css'

/** Which form is open: one at a time, in place on the page (DD-8). */
type OpenForm = { kind: 'add' } | { kind: 'edit'; id: string } | null

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

export function MedicationsPage() {
  const patientId = usePatientId()
  const patient = usePatient(patientId)
  const medications = useMedications(patientId)
  // The patient's today, from the server: dates show a year only when it isn't this one (DD-6, DD-7).
  const today = useTodayDoses(patientId).data
  const [showStopped, setShowStopped] = useState(false)
  const [open, setOpen] = useState<OpenForm>(null)
  // The count remounts the notice, so a second save in a row takes focus again.
  const [saved, setSaved] = useState<{ message: string; count: number } | null>(null)
  // After Cancel, focus goes back to the button that opened the form: 'add' or a medication id.
  const [returnFocus, setReturnFocus] = useState<string | null>(null)

  const focusIf = (target: string) => (returnFocus === target ? focusOnAttach : undefined)
  const openForm = (form: OpenForm) => {
    setOpen(form)
    setSaved(null)
    setReturnFocus(null)
  }
  const cancel = (focusTarget: string) => () => {
    setOpen(null)
    setReturnFocus(focusTarget)
  }
  const onSaved = (message: string) => {
    setOpen(null)
    setSaved((previous) => ({ message, count: (previous?.count ?? 0) + 1 }))
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
    const hasStopped = medications.data.some((medication) => !medication.active)
    const shown = medications.data.filter((medication) => showStopped || medication.active)
    content = (
      <>
        {saved === null ? null : (
          <div key={saved.count} ref={focusOnAttach} tabIndex={-1}>
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
        {medications.data.length === 0 && open === null ? (
          <EmptyState title={copy.meds.empty.title} body={copy.meds.empty.body} />
        ) : null}
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
        {shown.length === 0 ? null : (
          // role="list" because Safari drops list semantics when list-style is none.
          <ul role="list" className={styles.list}>
            {shown.map((medication) => (
              <li key={medication.id}>
                {open?.kind === 'edit' && open.id === medication.id ? (
                  <MedicationForm
                    patientId={patientId}
                    medication={medication}
                    onSaved={onSaved}
                    onCancel={cancel(medication.id)}
                  />
                ) : (
                  <MedicationItem
                    medication={medication}
                    timeZone={today?.timezone ?? patient.data?.timezone}
                    currentYear={today?.date.slice(0, 4)}
                    onEdit={
                      medication.active
                        ? () => {
                            openForm({ kind: 'edit', id: medication.id })
                          }
                        : undefined
                    }
                    editRef={focusIf(medication.id)}
                  />
                )}
              </li>
            ))}
          </ul>
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
