import { useId } from 'react'
import { doseKey, type PlannedDose } from '../../api/doses'
import { DoseCard } from '../../components/DoseCard/DoseCard'
import { copy } from '../../copy'
import { groupOf, groupOrder } from './groups'
import styles from './today.module.css'

type Props = { doses: PlannedDose[]; timeZone: string; at: Date }

export function DoseGroups({ doses, timeZone, at }: Props) {
  const idPrefix = useId()
  return (
    <>
      {groupOrder.map((group) => {
        const members = doses.filter((dose) => groupOf(dose, at) === group)
        if (members.length === 0) return null
        const headingId = `${idPrefix}-${group}`
        return (
          <section key={group} className={styles.group}>
            <h2 id={headingId}>{copy.today.group[group]}</h2>
            {/* role="list" because Safari drops list semantics when list-style is none. */}
            <ul role="list" aria-labelledby={headingId} className={styles.list}>
              {members.map((dose) => (
                <li key={doseKey(dose)}>
                  <DoseCard dose={dose} timeZone={timeZone} at={at} />
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </>
  )
}
