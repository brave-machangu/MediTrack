import { Link } from 'react-router'
import { PageHeading } from '../components/PageHeading/PageHeading'
import { copy } from '../copy'
import styles from './pages.module.css'

/** Unknown address, or a patient that no longer exists. */
export function NotFoundPage({ message = copy.notFound.body }: { message?: string }) {
  return (
    <div className={styles.stack}>
      <PageHeading heading={copy.notFound.title} pageName={copy.notFound.title} />
      <p>{message}</p>
      <p>
        <Link to="/">{copy.notFound.action}</Link>
      </p>
    </div>
  )
}
