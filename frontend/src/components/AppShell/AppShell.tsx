import { Info } from 'lucide-react'
import { Link, Outlet, useMatch } from 'react-router'
import { isNotFound } from '../../api/errors'
import { usePatient } from '../../api/patients'
import { copy } from '../../copy'
import { NotFoundPage } from '../../pages/NotFoundPage'
import { Disclaimer } from '../Disclaimer/Disclaimer'
import styles from './AppShell.module.css'
import { PatientNav } from './PatientNav'

export function AppShell() {
  const patientId = useMatch('/patients/:patientId/*')?.params.patientId
  const patient = usePatient(patientId)
  const patientMissing = isNotFound(patient.error)

  return (
    <div className={styles.page}>
      <a className={styles.skipLink} href="#main">
        {copy.app.skipLink}
      </a>
      <div role="note" aria-label={copy.app.demoBannerLabel} className={styles.demo}>
        <div className={`${styles.inner} ${styles.demoInner}`}>
          <Info aria-hidden="true" className={styles.demoIcon} />
          <p>{copy.app.demoBanner}</p>
        </div>
      </div>
      <div className={styles.top}>
        <header className={`${styles.inner} ${styles.header}`}>
          <Link to="/" className={styles.appName}>
            {copy.app.name}
          </Link>
          {patient.data && <p className={styles.patient}>{copy.patient.current(patient.data.display_name)}</p>}
        </header>
        {patientId !== undefined && !patientMissing && <PatientNav patientId={patientId} />}
      </div>
      <main id="main" tabIndex={-1} className={`${styles.inner} ${styles.main}`}>
        {patientMissing ? <NotFoundPage message={copy.error.NOT_FOUND} /> : <Outlet />}
      </main>
      <footer className={styles.footer}>
        <div className={styles.inner}>
          <Disclaimer />
        </div>
      </footer>
    </div>
  )
}
