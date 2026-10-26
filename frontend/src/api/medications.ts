import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from './client'
import type { components } from './schema'

export type Medication = components['schemas']['Medication']
export type Schedule = components['schemas']['Schedule']
export type MedicationCreate = components['schemas']['MedicationCreate']

const medicationsKey = (patientId: string) => ['medications', patientId] as const

/**
 * All of a patient's medications, stopped ones included, ordered by name. One request covers both views of
 * the page, and it tells us whether "No medications yet" is true or the list only looks empty.
 */
export function useMedications(patientId: string) {
  return useQuery({
    queryKey: medicationsKey(patientId),
    queryFn: () =>
      request<Medication[]>(`/api/v1/patients/${encodeURIComponent(patientId)}/medications?include_inactive=true`),
  })
}

/** Adds a medication, or edits one when `medicationId` is given. */
export function useSaveMedication(patientId: string, medicationId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: MedicationCreate) =>
      medicationId === undefined
        ? request<Medication>(`/api/v1/patients/${encodeURIComponent(patientId)}/medications`, { method: 'POST', body })
        : request<Medication>(`/api/v1/medications/${encodeURIComponent(medicationId)}`, { method: 'PATCH', body }),
    // Names and dosages also show on Today, so dose data refreshes too. The form stays "Saving…" until both have.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: medicationsKey(patientId) }),
        queryClient.invalidateQueries({ queryKey: ['dose-data', patientId] }),
      ]),
  })
}
