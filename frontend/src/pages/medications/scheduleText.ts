import type { Schedule } from '../../api/medications'
import { copy } from '../../copy'
import { formatShortDate } from '../../dates'

// Day names and list joining come from Intl (en-GB, DESIGN.md §4.4), not from copy.ts.
const list = new Intl.ListFormat('en-GB', { style: 'long', type: 'conjunction' })
const weekday = new Intl.DateTimeFormat('en-GB', { weekday: 'long', timeZone: 'UTC' })

/** ISO weekday (1 = Monday … 7 = Sunday) as a name. 1 January 2024 was a Monday. */
export function dayName(isoDay: number): string {
  return weekday.format(new Date(Date.UTC(2024, 0, isoDay)))
}

/** "07:00 and 14:00". */
export function timesText(times: string[]): string {
  return list.format([...times].sort())
}

/** "Every day", "Monday to Friday", "Saturday and Sunday", or the days by name. */
export function daysText(days: number[]): string {
  const sorted = [...days].sort((a, b) => a - b)
  switch (sorted.join(',')) {
    case '1,2,3,4,5,6,7':
      return copy.schedule.everyDay
    case '1,2,3,4,5':
      return copy.schedule.weekdays
    case '6,7':
      return copy.schedule.weekend
    default:
      return list.format(sorted.map(dayName))
  }
}

/** "From 1 October, no end date" or "From 1 September to 12 October". */
export function datesText(schedule: Schedule, currentYear: string | undefined): string {
  const start = formatShortDate(schedule.start_date, currentYear)
  return schedule.end_date
    ? copy.schedule.fromTo(start, formatShortDate(schedule.end_date, currentYear))
    : copy.schedule.from(start)
}
