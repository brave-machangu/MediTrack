import { useState } from 'react'
import { useEndSchedule, useSaveSchedule, type Medication, type Schedule } from '../../api/medications'
import type { SummaryItem } from '../../components/Field/ErrorSummary'
import { copy } from '../../copy'
import { addDays, formatShortDate } from '../../dates'
import {
  hasErrors,
  scheduleValues,
  serverScheduleErrors,
  toScheduleBody,
  validateSchedule,
  type ScheduleErrors,
  type ScheduleValues,
} from './scheduleValues'

export type ChangeErrors = ScheduleErrors & { ends?: string }

type Options = {
  patientId: string
  medication: Medication
  schedule: Schedule
  /** The patient's today, the default end of the current schedule. */
  today: string | undefined
  currentYear: string | undefined
  /** Field ids for the summary's links. */
  summaryItems: (errors: ChangeErrors) => SummaryItem[]
  onSaved: (message: string) => void
}

/**
 * Changing a schedule that has records (requirements §4.4): end it, then create its replacement starting the
 * next day by default (AC-34). If the end works but the new schedule doesn't, Retry only re-sends the new one.
 */
export function useChangeSchedule({ patientId, medication, schedule, today, currentYear, summaryItems, onSaved }: Options) {
  const [ends, setEnds] = useState(today ?? '')
  const [startEdited, setStartEdited] = useState(false)
  const [next, setNext] = useState<ScheduleValues>(() => ({
    ...scheduleValues(schedule, ''),
    start: today === undefined ? '' : addDays(today, 1),
    end: '',
  }))
  // Set once the current schedule has been ended; from then on only the new schedule is sent.
  const [endedOn, setEndedOn] = useState<string | null>(null)
  const [errors, setErrors] = useState<ChangeErrors>({})
  const [summary, setSummary] = useState<{ attempt: number; items: SummaryItem[] } | null>(null)
  const endCurrent = useEndSchedule(patientId, schedule.id)
  const create = useSaveSchedule(patientId, { medicationId: medication.id })

  function showErrors(found: ChangeErrors) {
    setErrors(found)
    setSummary((previous) => ({ attempt: (previous?.attempt ?? 0) + 1, items: summaryItems(found) }))
  }

  function createReplacement() {
    create.mutate(toScheduleBody(next), {
      onSuccess: (created) => {
        onSaved(copy.changeSchedule.done(formatShortDate(created.start_date, currentYear)))
      },
      onError: (error) => {
        const server = serverScheduleErrors(error)
        if (server !== null) showErrors(server)
      },
    })
  }

  function submit() {
    const found: ChangeErrors = validateSchedule(next)
    if (endedOn === null && ends === '') found.ends = copy.changeSchedule.endRequired
    if (hasErrors(found)) {
      showErrors(found)
      return
    }
    setErrors({})
    setSummary(null)
    if (endedOn !== null) {
      createReplacement()
      return
    }
    endCurrent.mutate(ends, {
      onSuccess: () => {
        setEndedOn(ends)
        createReplacement()
      },
      onError: (error) => {
        const server = serverScheduleErrors(error)
        if (server?.end !== undefined) showErrors({ ends: server.end })
      },
    })
  }

  return {
    ends,
    next,
    endedOn,
    errors,
    summary,
    busy: endCurrent.isPending || create.isPending,
    /** A refusal that isn't about a field (an overlap, an outage), from whichever request failed last. */
    refusal: [endCurrent, create].find((request) => request.isError && serverScheduleErrors(request.error) === null)?.error ?? null,
    refusalKey: Math.max(endCurrent.submittedAt, create.submittedAt),
    setEnds: (value: string) => {
      setEnds(value)
      // The new schedule follows the end date (the next day) until it's set by hand (AC-34).
      if (!startEdited && value !== '') setNext((previous) => ({ ...previous, start: addDays(value, 1) }))
    },
    setNext: <K extends keyof ScheduleValues>(field: K, value: ScheduleValues[K]) => {
      if (field === 'start') setStartEdited(true)
      setNext((previous) => ({ ...previous, [field]: value }))
    },
    submit,
  }
}
