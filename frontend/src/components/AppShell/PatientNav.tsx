import { NavLink } from 'react-router'
import { copy } from '../../copy'
import styles from './AppShell.module.css'

const pages = [
  { path: 'today', label: copy.nav.today },
  { path: 'medications', label: copy.nav.medications },
  { path: 'missed', label: copy.nav.missed },
  { path: 'summary', label: copy.nav.summary },
] as const

export function PatientNav({ patientId }: { patientId: string }) {
  return (
    <nav aria-label={copy.app.navLabel}>
      <ul className={`${styles.inner} ${styles.navList}`}>
        {pages.map((page) => (
          <li key={page.path}>
            {/* NavLink sets aria-current="page" on the current page; the CSS styles that attribute. */}
            <NavLink to={`/patients/${encodeURIComponent(patientId)}/${page.path}`} className={styles.navLink}>
              {page.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
