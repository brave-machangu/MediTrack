import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request, requestNoContent } from './client'
import type { components } from './schema'

export type PlannedDose = components['schemas']['PlannedDose']
type DayDoses = components['schemas']['DayDoses']
type DoseLog = components['schemas']['DoseLog']
export type DoseLogCreate = components['schemas']['DoseLogCreate']

/** Today, Missed doses and Daily summary keys all start with this, so one invalidation refreshes them together. */
const doseDataKey = (patientId: string) => ['dose-data', patientId] as const
const todayKey = (patientId: string) => [...doseDataKey(patientId), 'today'] as const

/** Planned doses for the patient's local today. No `date` is sent, so the server picks the patient's today (AC-09). */
export function useTodayDoses(patientId: string) {
  return useQuery({
    queryKey: todayKey(patientId),
    queryFn: () => request<DayDoses>(`/api/v1/patients/${encodeURIComponent(patientId)}/doses`),
    // Statuses change with time and only the server may change them (DD-5).
    refetchInterval: 60_000,
  })
}

/**
 * Records a dose as taken or skipped. Whatever the answer, the day is refetched before the mutation
 * counts as finished, so the card shows "Saving…" until the server's view arrives and never shows a
 * success the server hasn't confirmed (NFR-08).
 */
export function useRecordDose(patientId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: DoseLogCreate) => request<DoseLog>('/api/v1/dose-logs', { method: 'POST', body }),
    // A 201 is the server's confirmation (NFR-08), so its record is shown at once; the refetch then confirms it.
    onSuccess: (log) => {
      queryClient.setQueryData<DayDoses>(todayKey(patientId), (day) =>
        day === undefined ? day : { ...day, doses: day.doses.map((dose) => (isFor(log, dose) ? withRecord(dose, log) : dose)) },
      )
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: doseDataKey(patientId) }),
  })
}

const isFor = (log: DoseLog, dose: PlannedDose) =>
  log.schedule_id === dose.schedule_id && log.scheduled_for === dose.scheduled_for

/** The dose as the server reports it once this record exists; status and `late` come from the server. */
const withRecord = (dose: PlannedDose, log: DoseLog): PlannedDose => ({
  ...dose,
  status: log.status,
  late: log.late,
  dose_log_id: log.id,
  recorded_at: log.recorded_at,
})

/** Deletes a dose record (undo); the dose goes back to its time-based status. */
export function useUndoDose(patientId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (doseLogId: string) =>
      requestNoContent(`/api/v1/dose-logs/${encodeURIComponent(doseLogId)}`, { method: 'DELETE' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: doseDataKey(patientId) }),
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
