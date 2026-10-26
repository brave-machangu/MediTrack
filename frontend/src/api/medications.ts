import { useQuery } from '@tanstack/react-query'
import { request } from './client'
import type { components } from './schema'

export type Medication = components['schemas']['Medication']
export type Schedule = components['schemas']['Schedule']

/**
 * All of a patient's medications, stopped ones included, ordered by name. One request covers both views of
 * the page, and it tells us whether "No medications yet" is true or the list only looks empty.
 */
export function useMedications(patientId: string) {
  return useQuery({
    queryKey: ['medications', patientId],
    queryFn: () =>
      request<Medication[]>(`/api/v1/patients/${encodeURIComponent(patientId)}/medications?include_inactive=true`),
  })
}
