import { copy } from '../../copy'

/** The medical-advice notice from requirements §3, word for word (AC-27). */
export function Disclaimer() {
  return <p>{copy.app.disclaimer}</p>
}
