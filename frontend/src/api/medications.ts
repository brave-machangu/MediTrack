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

/** Stops a medication (one-way in v1): no more doses are planned, past records stay (requirements §4.4). */
export function useStopMedication(patientId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (medicationId: string) =>
      request<Medication>(`/api/v1/medications/${encodeURIComponent(medicationId)}`, {
        method: 'PATCH',
        body: { active: false },
      }),
    onSuccess: () => refreshAfterChange(queryClient, patientId),
  })
}

/** Medication changes also change what Today, Missed doses and the summary show. */
function refreshAfterChange(queryClient: ReturnType<typeof useQueryClient>, patientId: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: medicationsKey(patientId) }),
    queryClient.invalidateQueries({ queryKey: ['dose-data', patientId] }),
  ])
}

/** Adds a medication, or edits one when `medicationId` is given. */
export function useSaveMedication(patientId: string, medicationId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: MedicationCreate) =>
      medicationId === undefined
        ? request<Medication>(`/api/v1/patients/${encodeURIComponent(patientId)}/medications`, { method: 'POST', body })
        : request<Medication>(`/api/v1/medications/${encodeURIComponent(medicationId)}`, { method: 'PATCH', body }),
    // The form stays "Saving…" until the refreshed lists arrive.
    onSuccess: () => refreshAfterChange(queryClient, patientId),
  })
}
