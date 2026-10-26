import { ApiError } from '../../api/client'
import type { Schedule, ScheduleCreate } from '../../api/medications'
import { copy } from '../../copy'

export type ScheduleValues = { times: string[]; days: number[]; start: string; end: string; grace: string }

export type ScheduleErrors = {
  /** By time index, so each message sits next to its own time. */
  times?: Partial<Record<number, string>>
  days?: string
  start?: string
  end?: string
  grace?: string
  /** Messages the form can't place next to a field. */
  other?: string[]
}

export const everyDay = [1, 2, 3, 4, 5, 6, 7]
export const MAX_TIMES = 12
const TIME = /^([01][0-9]|2[0-3]):[0-5][0-9]$/

/** A schedule's values for editing, or a new one's defaults: every day from the patient's today, 60 minutes. */
export function scheduleValues(schedule: Schedule | undefined, defaultStart: string): ScheduleValues {
  if (schedule === undefined) return { times: [''], days: everyDay, start: defaultStart, end: '', grace: '60' }
  return {
    times: [...schedule.times_of_day],
    days: [...schedule.days_of_week],
    start: schedule.start_date,
    end: schedule.end_date ?? '',
    grace: String(schedule.grace_period_minutes),
  }
}

/** The contract's rules for a schedule (AC-05), checked before sending so errors appear next to the fields. */
export function validateSchedule(values: ScheduleValues): ScheduleErrors {
  const errors: ScheduleErrors = {}
  const times: Partial<Record<number, string>> = {}
  values.times.forEach((time, index) => {
    if (!TIME.test(time)) times[index] = copy.scheduleForm.timeRequired
    else if (values.times.indexOf(time) < index) times[index] = copy.scheduleForm.timeDuplicate
  })
  if (Object.keys(times).length > 0) errors.times = times
  if (values.days.length === 0) errors.days = copy.scheduleForm.daysRequired
  if (values.start === '') errors.start = copy.scheduleForm.startRequired
  // ISO dates compare correctly as strings.
  else if (values.end !== '' && values.end < values.start) errors.end = copy.scheduleForm.endBeforeStart
  const grace = values.grace.trim()
  if (!/^\d{1,3}$/.test(grace) || Number(grace) > 240) errors.grace = copy.scheduleForm.graceRange
  return errors
}

export const hasErrors = (errors: ScheduleErrors) => Object.keys(errors).length > 0

export function toScheduleBody(values: ScheduleValues): ScheduleCreate {
  return {
    times_of_day: values.times,
    days_of_week: [...values.days].sort((a, b) => a - b),
    start_date: values.start,
    end_date: values.end === '' ? null : values.end,
    grace_period_minutes: Number(values.grace.trim()),
  }
}

/** A 422's `errors[]` placed on the schedule fields; `times_of_day[2]` goes to the third time. */
export function serverScheduleErrors(error: unknown): ScheduleErrors | null {
  if (!(error instanceof ApiError) || error.code !== 'VALIDATION_ERROR') return null
  const errors: ScheduleErrors = {}
  for (const { field, message } of error.fieldErrors) {
    const time = /^times_of_day(?:\[(\d+)\])?$/.exec(field)
    if (time !== null) errors.times = { ...errors.times, [Number(time[1] ?? 0)]: message }
    else if (field.startsWith('days_of_week')) errors.days = message
    else if (field === 'start_date') errors.start = message
    else if (field === 'end_date') errors.end = message
    else if (field === 'grace_period_minutes') errors.grace = message
    else errors.other = [...(errors.other ?? []), message]
  }
  return errors
}
