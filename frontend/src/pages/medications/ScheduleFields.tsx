import { Plus } from 'lucide-react'
import { useState } from 'react'
import { Button } from '../../components/Button/Button'
import fieldStyles from '../../components/Field/Field.module.css'
import { Fieldset } from '../../components/Field/Fieldset'
import { TextField } from '../../components/Field/TextField'
import { copy } from '../../copy'
import styles from './medications.module.css'
import { dayName } from './scheduleText'
import { everyDay, MAX_TIMES } from './scheduleValues'

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

export const timeFieldId = (idPrefix: string, index: number) => `${idPrefix}-time-${String(index)}`
export const dayFieldId = (idPrefix: string, day: number) => `${idPrefix}-day-${String(day)}`

type TimesProps = {
  idPrefix: string
  times: string[]
  errors: Partial<Record<number, string>> | undefined
  onChange: (times: string[]) => void
}

/** One native time input per time, with Remove from the second on; focus follows Add and Remove. */
export function TimesFieldset({ idPrefix, times, errors, onChange }: TimesProps) {
  const [focusIndex, setFocusIndex] = useState<number | null>(null)
  return (
    <Fieldset legend={copy.scheduleForm.times}>
      {times.map((time, index) => (
        // Keyed by position: times have no identity of their own, and the labels ("Time 2") describe position.
        <div key={index} className={styles.timeRow}>
          <TextField
            id={timeFieldId(idPrefix, index)}
            ref={focusIndex === index ? focusOnAttach : undefined}
            type="time"
            label={copy.scheduleForm.time(index + 1)}
            error={errors?.[index]}
            value={time}
            className={fieldStyles.short}
            onChange={(event) => {
              onChange(times.map((current, position) => (position === index ? event.target.value : current)))
            }}
          />
          {times.length > 1 ? (
            <Button
              variant="quiet"
              aria-label={copy.scheduleForm.removeTimeName(index + 1)}
              onClick={() => {
                onChange(times.filter((_, position) => position !== index))
                setFocusIndex(Math.max(0, index - 1))
              }}
            >
              {copy.scheduleForm.removeTime}
            </Button>
          ) : null}
        </div>
      ))}
      {times.length < MAX_TIMES ? (
        <Button
          variant="quiet"
          className={styles.quietAction}
          onClick={() => {
            onChange([...times, ''])
            setFocusIndex(times.length)
          }}
        >
          <Plus aria-hidden="true" />
          {copy.scheduleForm.addTime}
        </Button>
      ) : null}
    </Fieldset>
  )
}

type DaysProps = { idPrefix: string; days: number[]; error: string | undefined; onChange: (days: number[]) => void }

export function DaysFieldset({ idPrefix, days, error, onChange }: DaysProps) {
  return (
    <Fieldset legend={copy.scheduleForm.days} hint={copy.scheduleForm.daysHint} error={error}>
      <div className={styles.days}>
        {everyDay.map((day) => (
          <label key={day} className={fieldStyles.checkbox}>
            <input
              type="checkbox"
              id={dayFieldId(idPrefix, day)}
              checked={days.includes(day)}
              onChange={(event) => {
                onChange(event.target.checked ? [...days, day] : days.filter((existing) => existing !== day))
              }}
            />
            {dayName(day)}
          </label>
        ))}
      </div>
    </Fieldset>
  )
}
