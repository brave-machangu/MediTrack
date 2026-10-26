import { describe, expect, it } from 'vitest'
import { formatDate, formatTime, timeZoneLabel } from './dates'

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

  it('shows timezone names with spaces', () => {
    expect(timeZoneLabel('America/New_York')).toBe('America/New York')
  })
})
