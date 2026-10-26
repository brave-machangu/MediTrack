import { skipToken, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router'
import { request } from './client'
import type { components } from './schema'

export type Patient = components['schemas']['Patient']
export type PatientCreate = components['schemas']['PatientCreate']

// One prefix for the list and each patient, so a save refreshes both (the header shows the patient's name).
const patientKeys = {
  all: ['patients'] as const,
  detail: (patientId: string) => ['patients', patientId] as const,
}

function getPatient(patientId: string): Promise<Patient> {
  return request<Patient>(`/api/v1/patients/${encodeURIComponent(patientId)}`)
}

/** All patients, ordered by name. */
export function usePatients() {
  return useQuery({ queryKey: patientKeys.all, queryFn: () => request<Patient[]>('/api/v1/patients') })
}

export function usePatient(patientId: string | undefined) {
  return useQuery({
    queryKey: patientKeys.detail(patientId ?? ''),
    queryFn: patientId === undefined ? skipToken : () => getPatient(patientId),
  })
}

/** Adds a patient, or edits one when `patientId` is given. The timezone can't change once doses are recorded. */
export function useSavePatient(patientId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PatientCreate) =>
      patientId === undefined
        ? request<Patient>('/api/v1/patients', { method: 'POST', body })
        : request<Patient>(`/api/v1/patients/${encodeURIComponent(patientId)}`, { method: 'PATCH', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: patientKeys.all }),
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
