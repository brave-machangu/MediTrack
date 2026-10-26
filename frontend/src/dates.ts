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
