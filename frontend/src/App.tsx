import { useState } from 'react'
import Landing from './pages/Landing'
import Wizard from './components/Wizard'
import { useBlitzStore } from './store/useBlitzStore'

function App() {
  const { runId } = useBlitzStore()
  const [launched, setLaunched] = useState(false)

  if (launched || runId) {
    return (
      <div className="bg-cream text-ink min-h-screen">
        <Wizard />
      </div>
    )
  }

  return (
    <div className="bg-cream text-ink min-h-screen">
      <Landing onLaunch={() => setLaunched(true)} />
    </div>
  )
}

export default App
