import { describe, expect, it } from 'vitest'
import { formatDate, formatShortDate, formatTime, localDate, timeZoneLabel } from './dates'

describe('dates', () => {
  it('formats a calendar date the same whatever the machine timezone', () => {
    expect(formatDate('2026-10-26')).toBe('Monday 26 October')
  })

  it('formats an instant in the patient timezone, not the machine one (tests run in Asia/Tokyo)', () => {
    expect(formatTime('2026-10-26T06:05:00Z', 'Africa/Harare')).toBe('08:05')
    expect(formatTime('2026-10-26T12:05:00Z', 'America/New_York')).toBe('08:05')
  })

  it('uses a 24-hour clock', () => {
    expect(formatTime('2026-10-26T19:30:00Z', 'Africa/Harare')).toBe('21:30')
  })

  it('leaves out the year unless it differs from the current one (DD-6)', () => {
    expect(formatShortDate('2026-10-01', '2026')).toBe('1 October')
    expect(formatShortDate('2025-12-31', '2026')).toBe('31 December 2025')
  })

  it('finds the patient-local date of an instant', () => {
    expect(localDate('2026-10-12T23:30:00Z', 'Africa/Harare')).toBe('2026-10-13')
    expect(localDate('2026-10-12T23:30:00Z', 'America/New_York')).toBe('2026-10-12')
  })

  it('shows timezone names with spaces', () => {
    expect(timeZoneLabel('America/New_York')).toBe('America/New York')
  })
})
