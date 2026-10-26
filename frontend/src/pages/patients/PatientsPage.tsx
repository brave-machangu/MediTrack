import { Plus } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { usePatients } from '../../api/patients'
import { Button } from '../../components/Button/Button'
import { useOpenForm } from '../../components/Field/useOpenForm'
import { Notice } from '../../components/Notice/Notice'
import { PageHeading } from '../../components/PageHeading/PageHeading'
import { EmptyState, ErrorState, LoadingState } from '../../components/PageState/PageState'
import { copy } from '../../copy'
import { timeZoneLabel } from '../../dates'
import { PatientForm } from './PatientForm'
import styles from './patients.module.css'

type OpenForm = { kind: 'add' } | { kind: 'edit'; id: string }

export function PatientsPage() {
  const patients = usePatients()
  // Destructured: the hook hands out ref callbacks, and the React lint treats a whole object passed that way as a ref.
  const { open, saved, focusSaved, focusIf, openForm, cancel, onSaved } = useOpenForm<OpenForm>()

  let content: ReactNode
  if (patients.data === undefined) {
    content = patients.isError ? (
      <ErrorState
        title={copy.patients.error.title}
        error={patients.error}
        onRetry={() => void patients.refetch()}
        retrying={patients.isFetching}
      />
    ) : (
      <LoadingState label={copy.patients.loading} />
    )
  } else {
    content = (
      <>
        {saved === null ? null : (
          <div key={saved.count} ref={focusSaved} tabIndex={-1}>
            <Notice tone="success">
              <p>{saved.message}</p>
            </Notice>
          </div>
        )}
        {patients.data.length === 0 && open === null ? (
          <EmptyState title={copy.patients.empty.title} body={copy.patients.empty.body} />
        ) : null}
        {patients.data.length === 0 ? null : (
          // role="list" because Safari drops list semantics when list-style is none.
          <ul role="list" className={styles.list}>
            {patients.data.map((patient) =>
              open?.kind === 'edit' && open.id === patient.id ? (
                <li key={patient.id}>
                  <PatientForm patient={patient} onSaved={onSaved} onCancel={cancel(patient.id)} />
                </li>
              ) : (
                <li key={patient.id} className={styles.row}>
                  <Link id={`patient-${patient.id}`} to={`/patients/${encodeURIComponent(patient.id)}/today`} className={styles.name}>
                    {patient.display_name}
                  </Link>
                  <p className={styles.timezone}>{timeZoneLabel(patient.timezone)}</p>
                  <Button
                    ref={focusIf(patient.id)}
                    variant="quiet"
                    // The visible label is "Edit" on every row; the description says whose.
                    aria-describedby={`patient-${patient.id}`}
                    className={styles.quietAction}
                    onClick={() => {
                      openForm({ kind: 'edit', id: patient.id })
                    }}
                  >
                    {copy.patients.edit}
                  </Button>
                </li>
              ),
            )}
          </ul>
        )}
        {open?.kind === 'add' ? (
          <PatientForm onSaved={onSaved} onCancel={cancel('add')} />
        ) : (
          <Button
            ref={focusIf('add')}
            className={styles.add}
            onClick={() => {
              openForm({ kind: 'add' })
            }}
          >
            <Plus aria-hidden="true" />
            {copy.patients.add}
          </Button>
        )}
      </>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.intro}>
        <PageHeading heading={copy.patients.title} pageName={copy.patients.title} />
        <p>{copy.patients.intro}</p>
      </div>
      {content}
    </div>
  )
}
