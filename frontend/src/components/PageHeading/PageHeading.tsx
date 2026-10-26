import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router'
import { copy } from '../../copy'

type Props = {
  /** Visible `h1` text. */
  heading: string
  /** Page name for the browser tab, e.g. "Today". */
  pageName: string
  patientName?: string | undefined
}

/** The page's one `h1`. Also sets the document title and moves focus here after in-app navigation. */
export function PageHeading({ heading, pageName, patientName }: Props) {
  const ref = useRef<HTMLHeadingElement>(null)
  const { key } = useLocation()

  useEffect(() => {
    document.title = copy.doc.title(pageName, patientName)
  }, [pageName, patientName])

  useEffect(() => {
    // Screen readers announce the new page this way. The first load ("default") leaves focus at the
    // top of the document, so the skip link stays the first thing a keyboard user reaches.
    if (key !== 'default') ref.current?.focus()
  }, [key])

  return (
    <h1 ref={ref} tabIndex={-1}>
      {heading}
    </h1>
  )
}
