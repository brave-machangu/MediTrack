import { describe, expect, it } from 'vitest'
import { copy } from '../../copy'
import { everyDay, validateSchedule, type ScheduleValues } from './scheduleValues'

const valid: ScheduleValues = { times: ['08:00'], days: everyDay, start: '2026-11-01', end: '', grace: '60' }

describe('validateSchedule (AC-05)', () => {
  it('accepts a valid schedule', () => {
    expect(validateSchedule(valid)).toEqual({})
  })

  it.each([
    ['an empty time', { times: [''] }, { times: { 0: copy.scheduleForm.timeRequired } }],
    ['25:00', { times: ['25:00'] }, { times: { 0: copy.scheduleForm.timeRequired } }],
    ['8:00 without a leading zero', { times: ['8:00'] }, { times: { 0: copy.scheduleForm.timeRequired } }],
    ['a repeated time', { times: ['08:00', '20:00', '08:00'] }, { times: { 2: copy.scheduleForm.timeDuplicate } }],
    ['no days', { days: [] }, { days: copy.scheduleForm.daysRequired }],
    ['no start date', { start: '' }, { start: copy.scheduleForm.startRequired }],
    ['an end before the start', { end: '2026-10-31' }, { end: copy.scheduleForm.endBeforeStart }],
    ['a grace period over 240', { grace: '241' }, { grace: copy.scheduleForm.graceRange }],
    ['a grace period that is not a whole number', { grace: '1.5' }, { grace: copy.scheduleForm.graceRange }],
  ])('rejects %s', (_case, change, errors) => {
    expect(validateSchedule({ ...valid, ...change })).toEqual(errors)
  })

  it('accepts an end date on the start date and grace periods of 0 and 240', () => {
    expect(validateSchedule({ ...valid, end: '2026-11-01', grace: '0' })).toEqual({})
    expect(validateSchedule({ ...valid, grace: '240' })).toEqual({})
  })
})
