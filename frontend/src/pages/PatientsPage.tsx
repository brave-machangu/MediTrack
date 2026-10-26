import { PageHeading } from '../components/PageHeading/PageHeading'
import { copy } from '../copy'

// The patient list and forms arrive in MT-024.
export function PatientsPage() {
  return <PageHeading heading={copy.patients.title} pageName={copy.patients.title} />
}
