import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request, requestNoContent } from './client'
import type { components } from './schema'

export type PlannedDose = components['schemas']['PlannedDose']
type DayDoses = components['schemas']['DayDoses']
export type DoseLog = components['schemas']['DoseLog']
export type DoseLogCreate = components['schemas']['DoseLogCreate']
export type DailyAdherence = components['schemas']['DailyAdherence']

/** Today, Missed doses and Daily summary keys all start with this, so one invalidation refreshes them together. */
const doseDataKey = (patientId: string) => ['dose-data', patientId] as const
const todayKey = (patientId: string) => [...doseDataKey(patientId), 'today'] as const
const missedKey = (patientId: string) => [...doseDataKey(patientId), 'missed'] as const

// No `date` is sent, so the server picks the patient's today (AC-09).
const fetchToday = (patientId: string) => request<DayDoses>(`/api/v1/patients/${encodeURIComponent(patientId)}/doses`)

/** Planned doses for the patient's local today. */
export function useTodayDoses(patientId: string) {
  return useQuery({
    queryKey: todayKey(patientId),
    queryFn: () => fetchToday(patientId),
    // Statuses change with time and only the server may change them (DD-5).
    refetchInterval: 60_000,
  })
}

/** The patient's local today ("2026-10-26") from the Today query (DD-7), sharing its cache but not its 60-second refetch. */
export function usePatientToday(patientId: string) {
  return useQuery({ queryKey: todayKey(patientId), queryFn: () => fetchToday(patientId), select: (day) => day.date })
}

/** Patient-local dates, both included. */
export type DateRange = { from: string; to: string }

/**
 * Unrecorded doses past their grace period, newest first. Without a range the server covers the patient's
 * last 7 days (AC-22); a range may cover at most 31 days (AC-23).
 */
export function useMissedDoses(patientId: string, range: DateRange | undefined) {
  const query = range === undefined ? '' : `?${new URLSearchParams(range).toString()}`
  return useQuery({
    queryKey: [...missedKey(patientId), range ?? 'last-7-days'],
    queryFn: () => request<PlannedDose[]>(`/api/v1/patients/${encodeURIComponent(patientId)}/missed-doses${query}`),
  })
}

/** One patient-local date's counts and adherence. Without a date, the server uses the patient's today. */
export function useDailySummary(patientId: string, date: string | undefined) {
  const query = date === undefined ? '' : `?${new URLSearchParams({ date }).toString()}`
  return useQuery({
    queryKey: [...doseDataKey(patientId), 'summary', date ?? 'today'],
    queryFn: () => request<DailyAdherence>(`/api/v1/patients/${encodeURIComponent(patientId)}/adherence/daily${query}`),
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
      const recorded = (dose: PlannedDose) => (isFor(log, dose) ? withRecord(dose, log) : dose)
      queryClient.setQueryData<DayDoses>(todayKey(patientId), (day) =>
        day === undefined ? day : { ...day, doses: day.doses.map(recorded) },
      )
      queryClient.setQueriesData<PlannedDose[]>({ queryKey: missedKey(patientId) }, (doses) => doses?.map(recorded))
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: doseDataKey(patientId) }),
  })
}

const isFor = (log: DoseLog, dose: PlannedDose) =>
  log.schedule_id === dose.schedule_id && log.scheduled_for === dose.scheduled_for

/** The dose as the server reports it once this record exists; status and `late` come from the server. */
export const withRecord = (dose: PlannedDose, log: DoseLog): PlannedDose => ({
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
