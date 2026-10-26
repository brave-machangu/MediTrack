import type { OpenFormState as SharedOpenFormState } from '../../components/Field/useOpenForm'

/** The Medications page's forms and dialogs; one is open at a time. */
export type OpenForm =
  | { kind: 'add' }
  | { kind: 'edit'; id: string }
  | { kind: 'stop'; id: string }
  | { kind: 'add-schedule'; medicationId: string }
  | { kind: 'edit-schedule'; id: string }
  | { kind: 'delete-schedule'; id: string }
  | { kind: 'change-schedule'; id: string }
  | { kind: 'end-schedule'; id: string }

export type OpenFormState = SharedOpenFormState<OpenForm>
