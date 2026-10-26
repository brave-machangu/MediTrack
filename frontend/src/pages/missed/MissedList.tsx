import { useId, useState } from 'react'
import { doseKey, withRecord, type DoseLog, type PlannedDose } from '../../api/doses'
import { DoseCard } from '../../components/DoseCard/DoseCard'
import { formatDate } from '../../dates'
import styles from './missed.module.css'

type Props = { doses: PlannedDose[]; patientId: string; timeZone: string; at: Date; currentYear: string | undefined }

/** This page's record for a dose: the server's 201, or null once it was undone here. */
type Records = ReadonlyMap<string, DoseLog | null>

/**
 * Missed doses by date, newest first. As on Today (DD-1), the cards shown when the list mounted keep their place.
 * A dose recorded here leaves the server's list (AC-24), but its card stays with the confirmed record, and Undo
 * while the window is open, until the list is loaded again (DD-13).
 */
export function MissedList({ doses, patientId, timeZone, at, currentYear }: Props) {
  const idPrefix = useId()
  const [placed] = useState(doses)
  const [records, setRecords] = useState<Records>(() => new Map())
  const shown = visibleDoses(placed, doses, records)
  const dates = [...new Set(shown.map((dose) => dose.local_date))].sort().reverse()

  const setRecord = (key: string, log: DoseLog | null) => {
    setRecords((previous) => new Map(previous).set(key, log))
  }

  return (
    <>
      {dates.map((date) => {
        const headingId = `${idPrefix}-${date}`
        return (
          <section key={date} className={styles.group}>
            <h2 id={headingId}>{formatDate(date, currentYear)}</h2>
            {/* role="list" because Safari drops list semantics when list-style is none. */}
            <ul role="list" aria-labelledby={headingId} className={styles.list}>
              {shown
                .filter((dose) => dose.local_date === date)
                .map((dose) => (
                  <li key={doseKey(dose)}>
                    <DoseCard
                      dose={dose}
                      patientId={patientId}
                      timeZone={timeZone}
                      at={at}
                      showRecordUntil
                      onRecordChange={(log) => {
                        setRecord(doseKey(dose), log)
                      }}
                    />
                  </li>
                ))}
            </ul>
          </section>
        )
      })}
    </>
  )
}

/**
 * The placed cards in their order, each as the server now reports it. One the server no longer lists is shown
 * with this page's record (or as it was, after an undo here, until the refetch brings it back); without either,
 * it was recorded elsewhere and goes. Doses that weren't on screen at mount come after the placed ones.
 */
function visibleDoses(placed: PlannedDose[], current: PlannedDose[], records: Records): PlannedDose[] {
  const latest = new Map(current.map((dose) => [doseKey(dose), dose]))
  const placedKeys = new Set(placed.map(doseKey))
  return [
    ...placed.flatMap((dose) => {
      const reported = latest.get(doseKey(dose))
      if (reported !== undefined) return [reported]
      const record = records.get(doseKey(dose))
      if (record === undefined) return []
      return [record === null ? dose : withRecord(dose, record)]
    }),
    ...current.filter((dose) => !placedKeys.has(doseKey(dose))),
  ]
}
