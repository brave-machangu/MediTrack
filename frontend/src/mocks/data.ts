// Synthetic demo data only (docs/test-strategy.md §5). Demo Patient B lives in a different timezone,
// so screens and tests show patient-local times rather than the machine's.
import type { Patient } from '../api/patients'

export const TRACE_ID = '4bf92f3577b34da6a3ce929d0e0e4736'

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
