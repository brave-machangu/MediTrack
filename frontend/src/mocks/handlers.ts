import { http, HttpResponse, type JsonBodyType } from 'msw'
import type { Problem } from '../api/client'
import type { PlannedDose } from '../api/doses'
import type { Patient } from '../api/patients'
import type { components } from '../api/schema'
import { dayA, MOCK_DATE, MOCK_NOW, patientA, patients, TRACE_ID } from './data'

// Every API response carries X-Trace-Id (contract, NFR-10).
const traceHeaders = { 'X-Trace-Id': TRACE_ID }

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
    return json(dayOf(patient, patient.id === patientA.id ? dayA : []))
  }),
]
