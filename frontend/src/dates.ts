// Formatting rules from DESIGN.md §4.4: fixed en-GB locale, 24-hour clock, patient timezone for instants.
const locale = 'en-GB'

const calendarDate = new Intl.DateTimeFormat(locale, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

/**
 * A patient-local calendar date ("2026-10-26") as "Monday 26 October". It carries no timezone, so it is read as UTC.
 * Given the patient's current year, a date in another year gets it ("Monday 29 December 2025", DD-6); en-GB's own
 * year format would add a comma after the weekday.
 */
export function formatDate(isoDate: string, currentYear?: string): string {
  const date = calendarDate.format(new Date(`${isoDate}T00:00:00Z`))
  return currentYear === undefined || isoDate.startsWith(currentYear) ? date : `${date} ${isoDate.slice(0, 4)}`
}

const dayMonth = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', timeZone: 'UTC' })
const dayMonthYear = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

/** "2026-10-01" → "1 October", with the year only when it isn't the patient's current year (DD-6). */
export function formatShortDate(isoDate: string, currentYear: string | undefined): string {
  const format = currentYear === undefined || isoDate.startsWith(currentYear) ? dayMonth : dayMonthYear
  return format.format(new Date(`${isoDate}T00:00:00Z`))
}

const DAY_MS = 86_400_000

/** A calendar date `days` later ("2026-10-26" + 1 → "2026-10-27"), counted in UTC so DST can't shift it. */
export function addDays(isoDate: string, days: number): string {
  return new Date(Date.parse(`${isoDate}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10)
}

/** The patient-local calendar date ("2026-10-12") on which a UTC instant falls. */
export function localDate(instant: string, timeZone: string): string {
  // en-CA formats dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date(instant),
  )
}

/** A UTC instant as the patient's local 24-hour time, e.g. "08:05". */
export function formatTime(instant: string, timeZone: string): string {
  return new Intl.DateTimeFormat(locale, { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(
    new Date(instant),
  )
}

/** An IANA name for reading: "America/New_York" → "America/New York". */
export function timeZoneLabel(timeZone: string): string {
  return timeZone.replaceAll('_', ' ')
}

/** The browser's timezone: only for deciding whether to show the timezone note, never for patient data. */
export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}
