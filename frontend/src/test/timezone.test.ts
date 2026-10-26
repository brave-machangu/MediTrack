import { describe, expect, it } from 'vitest'

describe('test environment', () => {
  it('runs in Asia/Tokyo, so code that uses the machine timezone for patient data fails (AC-35)', () => {
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe('Asia/Tokyo')
    expect(new Date(0).getTimezoneOffset()).toBe(-540)
  })
})
