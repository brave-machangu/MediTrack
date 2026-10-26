import { useId, useState } from 'react'
import { doseKey, type PlannedDose } from '../../api/doses'
import { DoseCard } from '../../components/DoseCard/DoseCard'
import { copy } from '../../copy'
import { groupOf, groupOrder } from './groups'
import styles from './today.module.css'

type Props = { doses: PlannedDose[]; patientId: string; timeZone: string; at: Date }

/**
 * Cards keep the group they had when this list mounted (DD-1): a background refresh updates a card's
 * status but doesn't move it out from under the person's finger. TodayPage remounts the list on Refresh.
 */
export function DoseGroups({ doses, patientId, timeZone, at }: Props) {
  const idPrefix = useId()
  const [placement] = useState(() => new Map(doses.map((dose) => [doseKey(dose), groupOf(dose, at)])))
  const placedGroup = (dose: PlannedDose) => placement.get(doseKey(dose))
  return (
    <>
      {groupOrder.map((group) => {
        // A dose that wasn't on screen at mount goes by its current status, after the cards already shown.
        const members = doses
          .filter((dose) => (placedGroup(dose) ?? groupOf(dose, at)) === group)
          .sort((a, b) => Number(placedGroup(a) === undefined) - Number(placedGroup(b) === undefined))
        if (members.length === 0) return null
        const headingId = `${idPrefix}-${group}`
        return (
          <section key={group} className={styles.group}>
            <h2 id={headingId}>{copy.today.group[group]}</h2>
            {/* role="list" because Safari drops list semantics when list-style is none. */}
            <ul role="list" aria-labelledby={headingId} className={styles.list}>
              {members.map((dose) => (
                <li key={doseKey(dose)}>
                  <DoseCard dose={dose} patientId={patientId} timeZone={timeZone} at={at} />
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </>
  )
}
