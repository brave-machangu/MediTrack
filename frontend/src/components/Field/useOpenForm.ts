import { useState } from 'react'

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/**
 * A page's in-place form state (DESIGN.md §4.6, DD-8): one form or dialog open at a time, a "saved" message
 * that takes focus, and focus back on the button that opened a form when it's cancelled.
 */
export function useOpenForm<Form>() {
  const [open, setOpen] = useState<Form | null>(null)
  // The count remounts the message, so a second save in a row takes focus again.
  const [saved, setSaved] = useState<{ message: string; count: number } | null>(null)
  const [returnFocus, setReturnFocus] = useState<string | null>(null)

  return {
    open,
    saved,
    focusSaved: focusOnAttach,
    /** A ref callback for the button `target` names, which takes focus after a Cancel. */
    focusIf: (target: string) => (returnFocus === target ? focusOnAttach : undefined),
    openForm: (form: Form) => {
      setOpen(form)
      setSaved(null)
      setReturnFocus(null)
    },
    cancel: (focusTarget: string) => () => {
      setOpen(null)
      setReturnFocus(focusTarget)
    },
    onSaved: (message: string) => {
      setOpen(null)
      setSaved((previous) => ({ message, count: (previous?.count ?? 0) + 1 }))
    },
  }
}

export type OpenFormState<Form> = ReturnType<typeof useOpenForm<Form>>
