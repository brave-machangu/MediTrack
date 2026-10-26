import { useState } from 'react'

/** Which form or dialog is open: one at a time, forms in place on the page (DD-8). */
export type OpenForm =
  | { kind: 'add' }
  | { kind: 'edit'; id: string }
  | { kind: 'stop'; id: string }
  | { kind: 'add-schedule'; medicationId: string }
  | { kind: 'edit-schedule'; id: string }
  | { kind: 'delete-schedule'; id: string }
  | null

const focusOnAttach = (element: HTMLElement | null) => {
  element?.focus()
}

/**
 * The page's form state: one form or dialog at a time, a "saved" message that takes focus, and focus back on
 * the button that opened a form when it's cancelled (DESIGN.md §4.6).
 */
export function useOpenForm() {
  const [open, setOpen] = useState<OpenForm>(null)
  // The count remounts the message, so a second save in a row takes focus again.
  const [saved, setSaved] = useState<{ message: string; count: number } | null>(null)
  const [returnFocus, setReturnFocus] = useState<string | null>(null)

  return {
    open,
    saved,
    focusSaved: focusOnAttach,
    /** A ref callback for the button `target` names, which takes focus after a Cancel. */
    focusIf: (target: string) => (returnFocus === target ? focusOnAttach : undefined),
    openForm: (form: OpenForm) => {
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

export type OpenFormState = ReturnType<typeof useOpenForm>
