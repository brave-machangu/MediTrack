// Formatting rules from DESIGN.md §4.4: fixed en-GB locale, 24-hour clock, patient timezone for instants.
const locale = 'en-GB'

const calendarDate = new Intl.DateTimeFormat(locale, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

/** A patient-local calendar date ("2026-10-26") as "Monday 26 October". It carries no timezone, so it is read as UTC. */
export function formatDate(isoDate: string): string {
  return calendarDate.format(new Date(`${isoDate}T00:00:00Z`))
}

const dayMonth = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', timeZone: 'UTC' })
const dayMonthYear = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

/** "2026-10-01" → "1 October", with the year only when it isn't the patient's current year (DD-6). */
export function formatShortDate(isoDate: string, currentYear: string | undefined): string {
  const format = currentYear === undefined || isoDate.startsWith(currentYear) ? dayMonth : dayMonthYear
  return format.format(new Date(`${isoDate}T00:00:00Z`))
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
