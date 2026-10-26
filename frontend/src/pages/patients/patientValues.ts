import { ApiError } from '../../api/client'
import type { PatientCreate } from '../../api/patients'
import { copy } from '../../copy'

export type PatientValues = { name: string; timezone: string }
export type PatientErrors = Partial<Record<keyof PatientValues, string>> & { other?: string[] }

/** The contract's limits (PatientCreate), checked before sending. */
export function validatePatient(values: PatientValues): PatientErrors {
  const errors: PatientErrors = {}
  const name = values.name.trim()
  if (name === '') errors.name = copy.patientForm.nameRequired
  else if (name.length > 80) errors.name = copy.patientForm.nameTooLong
  if (values.timezone === '') errors.timezone = copy.patientForm.timezoneRequired
  return errors
}

export const toPatientBody = (values: PatientValues): PatientCreate => ({
  display_name: values.name.trim(),
  timezone: values.timezone,
})

/**
 * The server's answer placed on the fields: a 422's errors[] (AC-02), and PATIENT_HAS_LOGS next to Timezone,
 * since that is what can't change. Returns null for anything else.
 */
export function serverPatientErrors(error: unknown): PatientErrors | null {
  if (!(error instanceof ApiError)) return null
  if (error.code === 'PATIENT_HAS_LOGS') return { timezone: copy.error.PATIENT_HAS_LOGS }
  if (error.code !== 'VALIDATION_ERROR') return null
  const errors: PatientErrors = {}
  for (const { field, message } of error.fieldErrors) {
    if (field === 'display_name') errors.name = message
    else if (field === 'timezone') errors.timezone = message
    else errors.other = [...(errors.other ?? []), message]
  }
  return errors
}
