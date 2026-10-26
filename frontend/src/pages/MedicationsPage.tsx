import { useCurrentPatient } from '../api/patients'
import { PageHeading } from '../components/PageHeading/PageHeading'
import { copy } from '../copy'

// Medications and schedules arrive in MT-026.
export function MedicationsPage() {
  const patient = useCurrentPatient()
  return <PageHeading heading={copy.meds.title} pageName={copy.nav.medications} patientName={patient.data?.display_name} />
}
