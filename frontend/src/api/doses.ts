import { useQuery } from '@tanstack/react-query'
import { request } from './client'
import type { components } from './schema'

export type PlannedDose = components['schemas']['PlannedDose']
type DayDoses = components['schemas']['DayDoses']

/** Today, Missed doses and Daily summary keys all start with this, so one invalidation refreshes them together. */
const doseDataKey = (patientId: string) => ['dose-data', patientId] as const

/** Planned doses for the patient's local today. No `date` is sent, so the server picks the patient's today (AC-09). */
export function useTodayDoses(patientId: string) {
  return useQuery({
    queryKey: [...doseDataKey(patientId), 'today'],
    queryFn: () => request<DayDoses>(`/api/v1/patients/${encodeURIComponent(patientId)}/doses`),
    // Statuses change with time and only the server may change them (DD-5).
    refetchInterval: 60_000,
  })
}

/** Whether the server would accept a record for this dose at `at`. A display check only; the server enforces it. */
export function isLogWindowOpen(dose: PlannedDose, at: Date): boolean {
  const time = at.getTime()
  return Date.parse(dose.log_window_opens_at) <= time && time <= Date.parse(dose.log_window_closes_at)
}

/** Identifies one planned dose across refetches. */
export function doseKey(dose: PlannedDose): string {
  return `${dose.schedule_id}@${dose.scheduled_for}`
}
