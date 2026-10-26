import { http, HttpResponse, type JsonBodyType } from 'msw'
import type { Problem } from '../api/client'
import type { PlannedDose } from '../api/doses'
import type { Patient } from '../api/patients'
import type { components } from '../api/schema'
import { now } from '../clock'
import {
  isLogFor,
  medicationsA,
  MOCK_DATE,
  MOCK_NOW,
  patientA,
  patients,
  plannedA,
  seedLogsA,
  stoppedA,
  TRACE_ID,
  withLog,
} from './data'

type DoseLog = components['schemas']['DoseLog']
type DoseLogCreate = components['schemas']['DoseLogCreate']
type Medication = components['schemas']['Medication']
type MedicationCreate = components['schemas']['MedicationCreate']
type MedicationUpdate = components['schemas']['MedicationUpdate']
type Schedule = components['schemas']['Schedule']
type ScheduleCreate = components['schemas']['ScheduleCreate']
type ScheduleUpdate = components['schemas']['ScheduleUpdate']

// Every API response carries X-Trace-Id (contract, NFR-10).
const traceHeaders = { 'X-Trace-Id': TRACE_ID }
const GRACE_MS = 60 * 60_000

export function json(body: JsonBodyType, status = 200) {
  return HttpResponse.json(body, { status, headers: traceHeaders })
}

/** A problem+json error response shaped like the contract's `Problem`. */
export function problem(status: number, code: Problem['code'], title: string) {
  const body: Problem = { type: 'about:blank', title, status, code, trace_id: TRACE_ID }
  return HttpResponse.json(body, {
    status,
    headers: { ...traceHeaders, 'Content-Type': 'application/problem+json' },
  })
}

/** The `GET /patients/{id}/doses` body for a patient's mock day. */
export function dayOf(patient: Patient, doses: PlannedDose[]): components['schemas']['DayDoses'] {
  return { patient_id: patient.id, date: MOCK_DATE, timezone: patient.timezone, generated_at: MOCK_NOW, doses }
}

// Records and medications changed through the mock API. Tests reset them after each case (src/test/setup.ts).
let logs: DoseLog[] = []
let medications: Medication[] = []

export function resetMockData() {
  logs = [...seedLogsA]
  medications = [...medicationsA, stoppedA]
}
resetMockData()

function dayA(): PlannedDose[] {
  return plannedA.map((dose) => {
    const log = logs.find((existing) => isLogFor(existing, dose))
    return log === undefined ? dose : withLog(dose, log)
  })
}

/** POST /dose-logs with the backend's rules (requirements §4.2): planned dose, one record per dose, log window. */
export function recordMockDose(body: DoseLogCreate) {
  const dose = plannedA.find((planned) => isLogFor(body, planned))
  if (dose === undefined) return problem(422, 'DOSE_NOT_PLANNED', 'Dose is not planned')
  if (logs.some((existing) => isLogFor(existing, dose))) return problem(409, 'DUPLICATE_DOSE_LOG', 'Dose already recorded')
  const at = now().getTime()
  if (at < Date.parse(dose.log_window_opens_at) || at > Date.parse(dose.log_window_closes_at)) {
    return problem(422, 'OUTSIDE_LOG_WINDOW', 'Outside the log window')
  }
  const log: DoseLog = {
    id: crypto.randomUUID(),
    schedule_id: dose.schedule_id,
    scheduled_for: dose.scheduled_for,
    status: body.status,
    recorded_at: now().toISOString(),
    late: at > Date.parse(dose.scheduled_for) + GRACE_MS,
    note: body.note ?? null,
  }
  logs.push(log)
  return json(log, 201)
}

/** The contract's limits for medication fields, as the backend would report them (422). */
function medicationProblems(body: MedicationUpdate) {
  const errors: { field: string; message: string }[] = []
  if (body.name !== undefined && (body.name.trim() === '' || body.name.length > 100)) {
    errors.push({ field: 'name', message: 'Name must be 1 to 100 characters.' })
  }
  if (body.dosage_label !== undefined && (body.dosage_label.trim() === '' || body.dosage_label.length > 100)) {
    errors.push({ field: 'dosage_label', message: 'Dosage must be 1 to 100 characters.' })
  }
  if (body.instructions && body.instructions.length > 500) {
    errors.push({ field: 'instructions', message: 'Instructions must be 500 characters or fewer.' })
  }
  return errors
}

function validationProblem(errors: { field: string; message: string }[]) {
  const body: Problem = { type: 'about:blank', title: 'Invalid request', status: 422, code: 'VALIDATION_ERROR', errors, trace_id: TRACE_ID }
  return HttpResponse.json(body, { status: 422, headers: { ...traceHeaders, 'Content-Type': 'application/problem+json' } })
}

/** The contract's schedule rules (AC-05), as the backend would report them (422). */
function scheduleProblems(schedule: Omit<Schedule, 'id' | 'medication_id' | 'has_dose_logs'>) {
  const errors: { field: string; message: string }[] = []
  schedule.times_of_day.forEach((time, index) => {
    if (!/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(time) || schedule.times_of_day.indexOf(time) < index) {
      errors.push({ field: `times_of_day[${String(index)}]`, message: 'Use HH:MM, each time once.' })
    }
  })
  if (schedule.days_of_week.length === 0) errors.push({ field: 'days_of_week', message: 'Choose at least one day.' })
  if (schedule.end_date && schedule.end_date < schedule.start_date) {
    errors.push({ field: 'end_date', message: 'End date must be on or after the start date.' })
  }
  const grace = schedule.grace_period_minutes
  if (!Number.isInteger(grace) || grace < 0 || grace > 240) {
    errors.push({ field: 'grace_period_minutes', message: 'Use 0 to 240 minutes.' })
  }
  return errors
}

/** Requirements §4.4 / AC-34: schedules of one medication may not share a weekday in overlapping dates. */
function overlapsAnother(medication: Medication, schedule: Omit<Schedule, 'medication_id' | 'has_dose_logs'>) {
  const end = (date: string | null | undefined) => date ?? '9999-12-31'
  return medication.schedules.some(
    (other) =>
      other.id !== schedule.id &&
      schedule.start_date <= end(other.end_date) &&
      other.start_date <= end(schedule.end_date) &&
      schedule.days_of_week.some((day) => other.days_of_week.includes(day)),
  )
}

function findSchedule(id: unknown) {
  for (const medication of medications) {
    const schedule = medication.schedules.find((candidate) => candidate.id === id)
    if (schedule !== undefined) return { medication, schedule }
  }
  return undefined
}

function replaceSchedules(medicationId: string, schedules: Schedule[]) {
  medications = medications.map((med) => (med.id === medicationId ? { ...med, schedules } : med))
}

const findPatient = (id: unknown) => patients.find((patient) => patient.id === id)
const patientNotFound = () => problem(404, 'NOT_FOUND', 'Patient not found')

export const handlers = [
  http.get('/api/v1/patients', () => json(patients)),
  http.get('/api/v1/patients/:patientId', ({ params }) => {
    const patient = findPatient(params.patientId)
    return patient === undefined ? patientNotFound() : json(patient)
  }),
  http.get('/api/v1/patients/:patientId/doses', ({ params }) => {
    const patient = findPatient(params.patientId)
    if (patient === undefined) return patientNotFound()
    return json(dayOf(patient, patient.id === patientA.id ? dayA() : []))
  }),
  http.get('/api/v1/patients/:patientId/medications', ({ params, request }) => {
    const patient = findPatient(params.patientId)
    if (patient === undefined) return patientNotFound()
    const includeInactive = new URL(request.url).searchParams.get('include_inactive') === 'true'
    const own = medications.filter((med) => med.patient_id === patient.id && (includeInactive || med.active))
    return json(own.sort((a, b) => a.name.localeCompare(b.name)))
  }),
  http.post<{ patientId: string }, MedicationCreate>('/api/v1/patients/:patientId/medications', async ({ params, request }) => {
    const patient = findPatient(params.patientId)
    if (patient === undefined) return patientNotFound()
    const body = await request.json()
    const errors = medicationProblems(body)
    if (errors.length > 0) return validationProblem(errors)
    const created: Medication = {
      id: crypto.randomUUID(),
      patient_id: patient.id,
      name: body.name,
      dosage_label: body.dosage_label,
      instructions: body.instructions ?? null,
      active: true,
      deactivated_at: null,
      created_at: now().toISOString(),
      schedules: [],
    }
    medications.push(created)
    return json(created, 201)
  }),
  http.patch<{ medicationId: string }, MedicationUpdate>('/api/v1/medications/:medicationId', async ({ params, request }) => {
    const existing = medications.find((med) => med.id === params.medicationId)
    if (existing === undefined) return problem(404, 'NOT_FOUND', 'Medication not found')
    const body = await request.json()
    if (body.active === true && !existing.active) return problem(409, 'MEDICATION_INACTIVE', 'Medication is inactive')
    const errors = medicationProblems(body)
    if (errors.length > 0) return validationProblem(errors)
    const stopping = body.active === false && existing.active
    const updated: Medication = {
      ...existing,
      ...(body.name === undefined ? {} : { name: body.name }),
      ...(body.dosage_label === undefined ? {} : { dosage_label: body.dosage_label }),
      ...(body.instructions === undefined ? {} : { instructions: body.instructions }),
      ...(stopping ? { active: false, deactivated_at: now().toISOString() } : {}),
    }
    medications = medications.map((med) => (med.id === existing.id ? updated : med))
    return json(updated)
  }),
  http.post<{ medicationId: string }, ScheduleCreate>(
    '/api/v1/medications/:medicationId/schedules',
    async ({ params, request }) => {
      const medication = medications.find((med) => med.id === params.medicationId)
      if (medication === undefined) return problem(404, 'NOT_FOUND', 'Medication not found')
      if (!medication.active) return problem(409, 'MEDICATION_INACTIVE', 'Medication is inactive')
      const body = await request.json()
      const created: Schedule = {
        id: crypto.randomUUID(),
        medication_id: medication.id,
        times_of_day: body.times_of_day,
        days_of_week: body.days_of_week ?? [1, 2, 3, 4, 5, 6, 7],
        start_date: body.start_date,
        end_date: body.end_date ?? null,
        grace_period_minutes: body.grace_period_minutes,
        has_dose_logs: false,
      }
      const errors = scheduleProblems(created)
      if (errors.length > 0) return validationProblem(errors)
      if (overlapsAnother(medication, created)) return problem(409, 'SCHEDULE_OVERLAP', 'Schedule overlaps an existing schedule')
      replaceSchedules(medication.id, [...medication.schedules, created])
      return json(created, 201)
    },
  ),
  http.patch<{ scheduleId: string }, ScheduleUpdate>('/api/v1/schedules/:scheduleId', async ({ params, request }) => {
    const found = findSchedule(params.scheduleId)
    if (found === undefined) return problem(404, 'NOT_FOUND', 'Schedule not found')
    const { medication, schedule } = found
    const body = await request.json()
    // With records, only the end date may change, and not to before today (requirements §4.4).
    if (schedule.has_dose_logs && Object.keys(body).some((field) => field !== 'end_date')) {
      return problem(409, 'SCHEDULE_HAS_LOGS', 'Schedule has dose logs')
    }
    const updated: Schedule = { ...schedule, ...body, end_date: body.end_date === undefined ? schedule.end_date : body.end_date }
    const errors = scheduleProblems(updated)
    if (schedule.has_dose_logs && (updated.end_date ?? '9999-12-31') < MOCK_DATE) {
      errors.push({ field: 'end_date', message: 'End date must be on or after today and the last recorded dose.' })
    }
    if (errors.length > 0) return validationProblem(errors)
    if (overlapsAnother(medication, updated)) return problem(409, 'SCHEDULE_OVERLAP', 'Schedule overlaps an existing schedule')
    replaceSchedules(medication.id, medication.schedules.map((candidate) => (candidate.id === schedule.id ? updated : candidate)))
    return json(updated)
  }),
  http.delete('/api/v1/schedules/:scheduleId', ({ params }) => {
    const found = findSchedule(params.scheduleId)
    if (found === undefined) return problem(404, 'NOT_FOUND', 'Schedule not found')
    if (found.schedule.has_dose_logs) return problem(409, 'SCHEDULE_HAS_LOGS', 'Schedule has dose logs')
    replaceSchedules(found.medication.id, found.medication.schedules.filter((candidate) => candidate.id !== found.schedule.id))
    return new HttpResponse(null, { status: 204, headers: traceHeaders })
  }),
  http.post<never, DoseLogCreate>('/api/v1/dose-logs', async ({ request }) => recordMockDose(await request.json())),
  http.delete('/api/v1/dose-logs/:doseLogId', ({ params }) => {
    const before = logs.length
    logs = logs.filter((log) => log.id !== params.doseLogId)
    if (logs.length === before) return problem(404, 'NOT_FOUND', 'Dose record not found')
    return new HttpResponse(null, { status: 204, headers: traceHeaders })
  }),
]
