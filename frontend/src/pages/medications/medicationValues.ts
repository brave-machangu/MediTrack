import { ApiError } from '../../api/client'
import type { MedicationCreate } from '../../api/medications'
import { copy } from '../../copy'

export type MedicationValues = { name: string; dosage: string; instructions: string }
export type MedicationErrors = Partial<Record<keyof MedicationValues, string>>

/** The contract's limits (MedicationCreate), checked before sending so errors appear next to the fields. */
export function validateMedication(values: MedicationValues): MedicationErrors {
  const errors: MedicationErrors = {}
  const name = values.name.trim()
  const dosage = values.dosage.trim()
  if (name === '') errors.name = copy.medForm.nameRequired
  else if (name.length > 100) errors.name = copy.medForm.nameTooLong
  if (dosage === '') errors.dosage = copy.medForm.dosageRequired
  else if (dosage.length > 100) errors.dosage = copy.medForm.dosageTooLong
  if (values.instructions.trim().length > 500) errors.instructions = copy.medForm.instructionsTooLong
  return errors
}

export function toMedicationBody(values: MedicationValues): MedicationCreate {
  const instructions = values.instructions.trim()
  return { name: values.name.trim(), dosage_label: values.dosage.trim(), instructions: instructions === '' ? null : instructions }
}

const serverFields: Record<string, keyof MedicationValues | undefined> = {
  name: 'name',
  dosage_label: 'dosage',
  instructions: 'instructions',
}

/** A 422's `errors[]` as form errors; anything that isn't one of our fields comes back in `other`. */
export function serverMedicationErrors(error: unknown): { fields: MedicationErrors; other: string[] } | null {
  if (!(error instanceof ApiError) || error.code !== 'VALIDATION_ERROR') return null
  const fields: MedicationErrors = {}
  const other: string[] = []
  for (const { field, message } of error.fieldErrors) {
    const name = serverFields[field]
    if (name === undefined) other.push(message)
    else fields[name] = message
  }
  return { fields, other }
}
