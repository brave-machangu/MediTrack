import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles/tokens.css'
import './styles/base.css'

async function startMockApi() {
  // `npm run dev:mock` runs the app against synthetic data; the check is false in builds, so the mocks are left out.
  if (import.meta.env.MODE !== 'mock') return
  const { startMockWorker } = await import('./mocks/browser')
  await startMockWorker()
}

const container = document.getElementById('root')
if (container === null) throw new Error('index.html has no #root element')

void startMockApi().then(() => {
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
