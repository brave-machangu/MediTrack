import { ChevronDown } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import { Link, useMatch } from 'react-router'
import { usePatients } from '../../api/patients'
import { copy } from '../../copy'
import { Button } from '../Button/Button'
import styles from './AppShell.module.css'

/**
 * "Switch patient" (DD-9): a button that shows a list of links to the same page for another patient. A
 * disclosure, not a <select> that navigates on change, so nothing happens until a link is chosen (WCAG 3.2.2).
 */
export function PatientSwitcher({ patientId }: { patientId: string }) {
  const page = useMatch('/patients/:patientId/:page')?.params.page ?? 'today'
  const patients = usePatients()
  const [open, setOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelId = useId()
  const buttonId = useId()

  // With one patient there's nobody to switch to.
  if (patients.data !== undefined && patients.data.length < 2) return null

  const others = patients.data?.filter((patient) => patient.id !== patientId) ?? []
  return (
    <div
      className={styles.switcher}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          setOpen(false)
          buttonRef.current?.focus()
        }
      }}
    >
      <Button
        ref={buttonRef}
        id={buttonId}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => {
          setOpen((current) => !current)
        }}
      >
        {copy.patient.switch}
        <ChevronDown aria-hidden="true" className={open ? styles.chevronOpen : undefined} />
      </Button>
      {open ? (
        <div id={panelId}>
          {patients.isError ? (
            <>
              <p>{copy.patient.switchError}</p>
              <Button onClick={() => void patients.refetch()}>{copy.action.retry}</Button>
            </>
          ) : patients.data === undefined ? (
            <p role="status">{copy.patient.switchLoading}</p>
          ) : (
            // Named by its button, so screen readers announce "Switch patient, list".
            <ul role="list" aria-labelledby={buttonId} className={styles.switcherList}>
              {others.map((patient) => (
                <li key={patient.id}>
                  <Link to={`/patients/${encodeURIComponent(patient.id)}/${page}`} className={styles.switcherLink}>
                    {patient.display_name}
                  </Link>
                </li>
              ))}
              <li>
                <Link to="/" className={styles.switcherLink}>
                  {copy.patient.allPatients}
                </Link>
              </li>
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
