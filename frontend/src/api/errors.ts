import { copy } from '../copy'
import { ApiError, type Problem } from './client'

// Typed against the contract's enum: if api/openapi.yaml gains a Problem code, this stops compiling until it has copy.
const problemMessages: Record<Problem['code'], string> = {
  VALIDATION_ERROR: copy.error.VALIDATION_ERROR,
  NOT_FOUND: copy.error.NOT_FOUND,
  DUPLICATE_DOSE_LOG: copy.error.DUPLICATE_DOSE_LOG,
  DOSE_NOT_PLANNED: copy.error.DOSE_NOT_PLANNED,
  OUTSIDE_LOG_WINDOW: copy.error.OUTSIDE_LOG_WINDOW,
  SCHEDULE_HAS_LOGS: copy.error.SCHEDULE_HAS_LOGS,
  MEDICATION_INACTIVE: copy.error.MEDICATION_INACTIVE,
  PATIENT_HAS_LOGS: copy.error.PATIENT_HAS_LOGS,
  SCHEDULE_OVERLAP: copy.error.SCHEDULE_OVERLAP,
  INTERNAL_ERROR: copy.error.INTERNAL_ERROR,
  SERVICE_UNAVAILABLE: copy.error.SERVICE_UNAVAILABLE,
}

function isProblemCode(code: string): code is Problem['code'] {
  return Object.hasOwn(problemMessages, code)
}

/** Plain-language message for any failed request. */
export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return copy.error.INTERNAL_ERROR
  if (error.kind === 'network') return copy.error.network
  if (error.kind === 'timeout') return copy.error.timeout
  if (error.code !== undefined && isProblemCode(error.code)) return problemMessages[error.code]
  return error.status === 503 ? copy.error.SERVICE_UNAVAILABLE : copy.error.INTERNAL_ERROR
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}
