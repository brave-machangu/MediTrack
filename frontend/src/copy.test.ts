import { describe, expect, it } from 'vitest'
import requirements from '../../docs/requirements.md?raw'
import { copy } from './copy'
import copySource from './copy.ts?raw'

// docs/test-strategy.md §3.7. The file itself is scanned, so strings added later are checked too.
const bannedPhrases = [
  /take (it|them|the dose|your dose)? ?(now|as soon as)/i,
  /double/i,
  /extra dose/i,
  /make up for/i,
  /catch up/i,
  /skip the next/i,
  /wait until/i,
  /should take/i,
  /you need to take/i,
]

describe('UI copy (src/copy.ts)', () => {
  it.each(bannedPhrases)('never says anything matching %s (AC-38)', (phrase) => {
    expect(copySource).not.toMatch(phrase)
  })

  it('has no exclamation marks', () => {
    expect(copySource).not.toMatch(/!(?!=)/)
  })

  it('uses the disclaimer from requirements §3 word for word (AC-27)', () => {
    expect(requirements).toContain(copy.app.disclaimer)
  })

  it('uses the demo banner from FR-13 word for word (AC-40)', () => {
    expect(requirements).toContain(copy.app.demoBanner)
  })
})
