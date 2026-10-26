import { useDeleteSchedule, useStopMedication, type Medication, type Schedule } from '../../api/medications'
import { ConfirmDialog } from '../../components/ConfirmDialog/ConfirmDialog'
import { copy } from '../../copy'
import { scheduleSentence } from './scheduleText'

// Each dialog owns its request, so it opens with no error left over from last time.

type StopProps = { patientId: string; medication: Medication; onDone: (message: string) => void; onCancel: () => void }

export function StopMedicationDialog({ patientId, medication, onDone, onCancel }: StopProps) {
  const stop = useStopMedication(patientId)
  return (
    <ConfirmDialog
      title={copy.stopConfirm.title(medication.name)}
      body={copy.stopConfirm.body}
      confirmLabel={copy.stopConfirm.confirm}
      busy={stop.isPending}
      error={stop.error}
      onConfirm={() => {
        stop.mutate(medication.id, {
          onSuccess: () => {
            onDone(copy.meds.stopped(medication.name))
          },
        })
      }}
      onCancel={onCancel}
    />
  )
}

type DeleteProps = {
  patientId: string
  schedule: Schedule
  currentYear: string | undefined
  onDone: (message: string) => void
  onCancel: () => void
}

export function DeleteScheduleDialog({ patientId, schedule, currentYear, onDone, onCancel }: DeleteProps) {
  const remove = useDeleteSchedule(patientId)
  return (
    <ConfirmDialog
      title={copy.deleteSchedule.title}
      body={copy.deleteSchedule.body(scheduleSentence(schedule, currentYear))}
      confirmLabel={copy.deleteSchedule.confirm}
      busy={remove.isPending}
      error={remove.error}
      onConfirm={() => {
        remove.mutate(schedule.id, {
          onSuccess: () => {
            onDone(copy.deleteSchedule.done)
          },
        })
      }}
      onCancel={onCancel}
    />
  )
}
