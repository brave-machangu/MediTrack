import { useCurrentPatient } from '../api/patients'
import { PageHeading } from '../components/PageHeading/PageHeading'
import { copy } from '../copy'

// The dose list arrives in MT-025; until the day's date is loaded the heading is just "Today".
export function TodayPage() {
  const patient = useCurrentPatient()
  return <PageHeading heading={copy.today.titleLoading} pageName={copy.nav.today} patientName={patient.data?.display_name} />
}
