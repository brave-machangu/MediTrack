import { delay, http, type RequestHandler } from 'msw'
import { problem } from './handlers'

const todayDoses = '/api/v1/patients/:patientId/doses'
const doseLogs = '/api/v1/dose-logs'
const medications = '/api/v1/patients/:patientId/medications'
const patientList = '/api/v1/patients'
const outage = () => problem(503, 'SERVICE_UNAVAILABLE', 'Service unavailable')

/**
 * Extra states for `npm run dev:mock` and the screenshots, chosen with `?mock=<name>` in the URL.
 * Each one is created fresh, so state such as a call count starts again with every page load.
 */
export const scenarios: Record<string, () => RequestHandler[]> = {
  'today-loading': () => [
    http.get(todayDoses, async () => {
      await delay('infinite')
    }),
  ],
  'today-error': () => [http.get(todayDoses, outage)],
  'record-slow': () => [
    http.post(doseLogs, async () => {
      await delay('infinite')
    }),
  ],
  'record-error': () => [http.post(doseLogs, () => problem(500, 'INTERNAL_ERROR', 'Internal error'))],
  'medications-loading': () => [
    http.get(medications, async () => {
      await delay('infinite')
    }),
  ],
  'medications-error': () => [http.get(medications, outage)],
  'patients-loading': () => [
    http.get(patientList, async () => {
      await delay('infinite')
    }),
  ],
  'patients-error': () => [http.get(patientList, outage)],
  // The first load works and later ones fail, which leaves stale data on screen.
  'today-stale': () => {
    let calls = 0
    return [
      http.get(todayDoses, () => {
        calls += 1
        return calls === 1 ? undefined : outage()
      }),
    ]
  },
}
