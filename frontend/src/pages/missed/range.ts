import { ApiError } from '../../api/client'
import type { DateRange } from '../../api/doses'
import { copy } from '../../copy'
import { addDays } from '../../dates'

/** Messages by place: next to From, next to To, for the range as a whole, or in the summary only. */
export type RangeErrors = { from?: string; to?: string; range?: string; other?: string[] }

/** The server's default range: the patient's today and the 6 days before it (AC-22). */
export const lastSevenDays = (today: string): DateRange => ({ from: addDays(today, -6), to: today })

export const sameRange = (a: DateRange, b: DateRange) => a.from === b.from && a.to === b.to

/** The server's rules, checked first (DESIGN.md §4.6): both dates, From on or before To, at most 31 days (AC-23). */
export function rangeErrors({ from, to }: DateRange): RangeErrors {
  if (from === '' || to === '') {
    return {
      ...(from === '' ? { from: copy.missed.fromRequired } : {}),
      ...(to === '' ? { to: copy.missed.toRequired } : {}),
    }
  }
  if (from > to) return { range: copy.missed.fromAfterTo }
  // Both ends count, so 31 days means `to` is at most 30 days after `from`.
  if (addDays(from, 30) < to) return { range: copy.missed.tooLong }
  return {}
}

/**
 * A 422 for the range, by field. The contract doesn't name the fields for query parameters, so `from` and `to`
 * are assumed; any other field shows in the summary only.
 */
export function serverRangeErrors(error: unknown): RangeErrors | null {
  if (!(error instanceof ApiError) || error.code !== 'VALIDATION_ERROR') return null
  const errors: RangeErrors = {}
  for (const { field, message } of error.fieldErrors) {
    if (field === 'from' || field === 'to') errors[field] = message
    else errors.other = [...(errors.other ?? []), message]
  }
  return errors
}
