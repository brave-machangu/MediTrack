import { useCurrentPatient } from '../api/patients'
import { PageHeading } from '../components/PageHeading/PageHeading'
import { copy } from '../copy'

// Counts and adherence arrive in MT-028.
export function SummaryPage() {
  const patient = useCurrentPatient()
  return <PageHeading heading={copy.summary.title} pageName={copy.nav.summary} patientName={patient.data?.display_name} />
}
