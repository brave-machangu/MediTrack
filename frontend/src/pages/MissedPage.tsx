import { useCurrentPatient } from '../api/patients'
import { PageHeading } from '../components/PageHeading/PageHeading'
import { copy } from '../copy'

// The missed-dose list arrives in MT-027.
export function MissedPage() {
  const patient = useCurrentPatient()
  return <PageHeading heading={copy.missed.title} pageName={copy.nav.missed} patientName={patient.data?.display_name} />
}
