import { Navigate, type RouteObject } from 'react-router'
import { AppShell } from './components/AppShell/AppShell'
import { MedicationsPage } from './pages/medications/MedicationsPage'
import { MissedPage } from './pages/missed/MissedPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PatientsPage } from './pages/patients/PatientsPage'
import { SummaryPage } from './pages/summary/SummaryPage'
import { TodayPage } from './pages/today/TodayPage'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <PatientsPage /> },
      {
        path: 'patients/:patientId',
        children: [
          { index: true, element: <Navigate to="today" replace /> },
          { path: 'today', element: <TodayPage /> },
          { path: 'medications', element: <MedicationsPage /> },
          { path: 'missed', element: <MissedPage /> },
          { path: 'summary', element: <SummaryPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
