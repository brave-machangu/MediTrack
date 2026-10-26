import { useId } from 'react'
import type { DailyAdherence } from '../../api/doses'
import { copy } from '../../copy'
import { formatDate } from '../../dates'
import styles from './summary.module.css'

type Props = {
  summary: DailyAdherence
  currentYear: string | undefined
  /** After Show summary, the date heading takes focus so the new result is read out. */
  focusHeading: boolean
}

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/**
 * One day's adherence and counts (DESIGN.md §6.8), exactly as the API returns them. The percentage is never
 * coloured or labelled good or bad.
 */
export function DaySummary({ summary, currentYear, focusHeading }: Props) {
  const headingId = useId()
  const date = formatDate(summary.date, currentYear)
  const heading = (
    <h2 id={headingId} ref={focusHeading ? focusOnAttach : undefined} tabIndex={-1}>
      {date}
    </h2>
  )
  if (summary.planned === 0) {
    return (
      <section aria-labelledby={headingId} className={styles.day}>
        {heading}
        <p>{copy.summary.empty(date)}</p>
      </section>
    )
  }

  const rows = [
    { label: copy.summary.planned, value: summary.planned },
    { label: copy.summary.taken, value: summary.taken },
    { label: copy.summary.takenLate, value: summary.taken_late, part: true },
    { label: copy.summary.skipped, value: summary.skipped },
    { label: copy.summary.missed, value: summary.missed },
    { label: copy.summary.pending, value: summary.pending },
  ]
  return (
    <section aria-labelledby={headingId} className={styles.day}>
      {heading}
      <div className={styles.adherence}>
        <h3>{copy.summary.adherence}</h3>
        {summary.adherence_percent === null ? (
          // AC-26: nothing taken, skipped or missed yet, so there's nothing to score.
          <p className={styles.noScore}>{copy.summary.noScore}</p>
        ) : (
          // One decimal place, as the API returns it ("50.0%").
          <p className={styles.percent}>{copy.summary.percent(summary.adherence_percent.toFixed(1))}</p>
        )}
        <p className={styles.note}>
          {summary.adherence_percent === null ? copy.summary.noScoreExplain : copy.summary.adherenceExplain}
        </p>
      </div>
      <table className={styles.table}>
        <caption>{copy.summary.tableCaption(date)}</caption>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row" className={row.part ? styles.part : undefined}>
                {row.label}
              </th>
              <td>{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
