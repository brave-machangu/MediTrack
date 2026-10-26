import { http, HttpResponse, type JsonBodyType } from 'msw'
import type { Problem } from '../api/client'
import type { PlannedDose } from '../api/doses'
import type { Patient } from '../api/patients'
import type { components } from '../api/schema'
import { now } from '../clock'
import { isLogFor, MOCK_DATE, MOCK_NOW, patientA, patients, plannedA, seedLogsA, TRACE_ID, withLog } from './data'

type DoseLog = components['schemas']['DoseLog']
type DoseLogCreate = components['schemas']['DoseLogCreate']

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

// Dose records made through the mock API. Tests reset them after each case (src/test/setup.ts).
let logs: DoseLog[] = []

export function resetMockLogs() {
  logs = [...seedLogsA]
}
resetMockLogs()

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
  http.post<never, DoseLogCreate>('/api/v1/dose-logs', async ({ request }) => recordMockDose(await request.json())),
  http.delete('/api/v1/dose-logs/:doseLogId', ({ params }) => {
    const before = logs.length
    logs = logs.filter((log) => log.id !== params.doseLogId)
    if (logs.length === before) return problem(404, 'NOT_FOUND', 'Dose record not found')
    return new HttpResponse(null, { status: 204, headers: traceHeaders })
  }),
]
