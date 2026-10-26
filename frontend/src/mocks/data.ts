// Synthetic demo data only (docs/test-strategy.md §5). Demo Patient B lives in a different timezone,
// so screens and tests show patient-local times rather than the machine's.
import type { PlannedDose } from '../api/doses'
import type { Patient } from '../api/patients'
import type { components } from '../api/schema'

export const TRACE_ID = '4bf92f3577b34da6a3ce929d0e0e4736'

/** The mock day. Tests and screenshots fix the clock at MOCK_NOW: 09:10 on Monday 26 October in Africa/Harare. */
export const MOCK_DATE = '2026-10-26'
export const MOCK_NOW = '2026-10-26T07:10:00Z'

export const patientA: Patient = {
  id: '6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a01',
  display_name: 'Demo Patient A',
  timezone: 'Africa/Harare',
  created_at: '2026-10-01T06:00:00Z',
}

export const patientB: Patient = {
  id: '6f0c2a7e-1b54-4c3e-9a1d-2b7f4e8c5a02',
  display_name: 'Demo Patient B',
  timezone: 'America/New_York',
  created_at: '2026-10-01T12:00:00Z',
}

export const patients = [patientA, patientB]

type Medication = Pick<PlannedDose, 'medication_id' | 'schedule_id' | 'medication_name' | 'dosage_label' | 'instructions'>

const alpha: Medication = {
  medication_id: '0d6b8a52-7c3e-4f1a-8b2d-1e5f9c3a7b01',
  schedule_id: '5a1e7c93-2b4d-4e6f-9a8c-3d7b1f5e9c01',
  medication_name: 'Demo Med Alpha',
  dosage_label: '500 mg, 1 tablet',
  instructions: 'With food',
}
const beta: Medication = {
  medication_id: '0d6b8a52-7c3e-4f1a-8b2d-1e5f9c3a7b02',
  schedule_id: '5a1e7c93-2b4d-4e6f-9a8c-3d7b1f5e9c02',
  medication_name: 'Demo Med Beta',
  dosage_label: '1 tablet',
  instructions: null,
}
const gamma: Medication = {
  medication_id: '0d6b8a52-7c3e-4f1a-8b2d-1e5f9c3a7b03',
  schedule_id: '5a1e7c93-2b4d-4e6f-9a8c-3d7b1f5e9c03',
  medication_name: 'Demo Med Gamma',
  dosage_label: '2 drops',
  instructions: null,
}
const delta: Medication = {
  medication_id: '0d6b8a52-7c3e-4f1a-8b2d-1e5f9c3a7b04',
  schedule_id: '5a1e7c93-2b4d-4e6f-9a8c-3d7b1f5e9c04',
  medication_name: 'Demo Med Delta Extended Release Capsules',
  dosage_label: '1 capsule',
  instructions: null,
}

const HOUR = 3_600_000
const iso = (ms: number) => new Date(ms).toISOString().replace('.000Z', 'Z')

type DoseLog = components['schemas']['DoseLog']

/** A planned dose with no record. `status` is what the server reports while nothing is logged. */
function planned(med: Medication, localTime: string, scheduledFor: string, status: PlannedDose['status']): PlannedDose {
  const scheduled = Date.parse(scheduledFor)
  return {
    ...med,
    scheduled_for: scheduledFor,
    local_date: MOCK_DATE,
    local_time: localTime,
    status,
    late: false,
    // The backend's default log window: from 1 hour before to 24 hours after the dose time.
    log_window_opens_at: iso(scheduled - HOUR),
    log_window_closes_at: iso(scheduled + 24 * HOUR),
    dose_log_id: null,
    recorded_at: null,
  }
}

/** How GET /doses shows a planned dose once it has a record. */
export function withLog(dose: PlannedDose, log: DoseLog): PlannedDose {
  return { ...dose, status: log.status, late: log.late, dose_log_id: log.id, recorded_at: log.recorded_at }
}

export function isLogFor(log: Pick<DoseLog, 'schedule_id' | 'scheduled_for'>, dose: PlannedDose): boolean {
  return log.schedule_id === dose.schedule_id && log.scheduled_for === dose.scheduled_for
}

const gamma0600 = planned(gamma, '06:00', '2026-10-26T04:00:00Z', 'missed')
const alpha0700 = planned(alpha, '07:00', '2026-10-26T05:00:00Z', 'missed')
const beta0730 = planned(beta, '07:30', '2026-10-26T05:30:00Z', 'missed')
const delta0830 = planned(delta, '08:30', '2026-10-26T06:30:00Z', 'due')
const gamma0900 = planned(gamma, '09:00', '2026-10-26T07:00:00Z', 'due')
const alpha1400 = planned(alpha, '14:00', '2026-10-26T12:00:00Z', 'upcoming')
const beta2100 = planned(beta, '21:00', '2026-10-26T19:00:00Z', 'upcoming')

/** Demo Patient A's planned doses at MOCK_NOW, before any records. */
export const plannedA = [gamma0600, alpha0700, beta0730, delta0830, gamma0900, alpha1400, beta2100]

function seedLog(dose: PlannedDose, id: string, status: DoseLog['status'], recordedAt: string, late: boolean): DoseLog {
  return { id, schedule_id: dose.schedule_id, scheduled_for: dose.scheduled_for, status, recorded_at: recordedAt, late, note: null }
}

/** Records already made that morning. */
export const seedLogsA: DoseLog[] = [
  seedLog(alpha0700, '9c4f2e81-6a3b-4d5c-8e7f-2a1b3c4d5e01', 'taken', '2026-10-26T06:20:00Z', true),
  seedLog(beta0730, '9c4f2e81-6a3b-4d5c-8e7f-2a1b3c4d5e02', 'taken', '2026-10-26T05:32:00Z', false),
  seedLog(gamma0900, '9c4f2e81-6a3b-4d5c-8e7f-2a1b3c4d5e03', 'skipped', '2026-10-26T06:50:00Z', false),
]

/** Demo Patient A's day as GET /doses returns it at MOCK_NOW: every status, a long name, doses without instructions. */
export const dayA: PlannedDose[] = plannedA.map((dose) => {
  const log = seedLogsA.find((seed) => isLogFor(seed, dose))
  return log === undefined ? dose : withLog(dose, log)
})
