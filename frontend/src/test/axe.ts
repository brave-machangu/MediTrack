import axe from 'axe-core'

/**
 * IDs of serious or critical axe violations in the document (AC-28 bar). jsdom has no layout,
 * so colour contrast is not checked here; DESIGN.md §2.1 lists the measured ratios instead.
 */
export async function seriousAxeViolations(): Promise<string[]> {
  const results = await axe.run(document, { resultTypes: ['violations'] })
  return results.violations
    .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
    .map((violation) => violation.id)
}
