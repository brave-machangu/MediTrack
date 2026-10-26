import { http, HttpResponse, type JsonBodyType } from 'msw'
import type { Problem } from '../api/client'
import { patients, TRACE_ID } from './data'

// Every API response carries X-Trace-Id (contract, NFR-10).
const traceHeaders = { 'X-Trace-Id': TRACE_ID }

function json(body: JsonBodyType, status = 200) {
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

export const handlers = [
  http.get('/api/v1/patients', () => json(patients)),
  http.get('/api/v1/patients/:patientId', ({ params }) => {
    const patient = patients.find((p) => p.id === params.patientId)
    return patient === undefined ? problem(404, 'NOT_FOUND', 'Patient not found') : json(patient)
  }),
]
