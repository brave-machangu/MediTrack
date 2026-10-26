import { skipToken, useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router'
import { request } from './client'
import type { components } from './schema'

export type Patient = components['schemas']['Patient']

const patientKeys = {
  detail: (patientId: string) => ['patients', patientId] as const,
}

function getPatient(patientId: string): Promise<Patient> {
  return request<Patient>(`/api/v1/patients/${encodeURIComponent(patientId)}`)
}

export function usePatient(patientId: string | undefined) {
  return useQuery({
    queryKey: patientKeys.detail(patientId ?? ''),
    queryFn: patientId === undefined ? skipToken : () => getPatient(patientId),
  })
}

/** The `:patientId` of a patient page; those pages only render under `/patients/:patientId`. */
export function usePatientId(): string {
  const { patientId } = useParams()
  if (patientId === undefined) throw new Error('Patient pages need a :patientId route parameter')
  return patientId
}

/** The patient named in the current URL (`/patients/:patientId/...`). */
export function useCurrentPatient() {
  return usePatient(usePatientId())
}
