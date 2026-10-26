import { describe, expect, it } from 'vitest'
import { copy } from '../../copy'
import { daysText, timesText } from './scheduleText'

describe('schedule text', () => {
  it('lists times in order, joined in plain English', () => {
    expect(timesText(['20:00', '08:00'])).toBe('08:00 and 20:00')
    expect(timesText(['08:00'])).toBe('08:00')
  })

  it.each([
    [[1, 2, 3, 4, 5, 6, 7], copy.schedule.everyDay],
    [[5, 4, 3, 2, 1], copy.schedule.weekdays],
    [[7, 6], copy.schedule.weekend],
    [[1, 3, 5], 'Monday, Wednesday and Friday'],
    [[7], 'Sunday'],
  ])('describes days %j as "%s"', (days, text) => {
    expect(daysText(days)).toBe(text)
  })
})
