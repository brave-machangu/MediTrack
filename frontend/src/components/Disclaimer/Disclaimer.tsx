import { copy } from '../../copy'
import styles from './Disclaimer.module.css'

/**
 * The medical-advice notice from requirements §3, word for word (AC-27). The inset on Missed doses repeats only
 * its last sentence, so that page says nothing more than that a dose wasn't recorded (DD-4, AC-38).
 */
export function Disclaimer({ inset = false }: { inset?: boolean }) {
  return inset ? <p className={styles.inset}>{copy.app.disclaimerInset}</p> : <p>{copy.app.disclaimer}</p>
}
