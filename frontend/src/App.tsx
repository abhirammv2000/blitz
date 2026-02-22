import { useState } from 'react'
import Landing from './pages/Landing'
import Wizard from './components/Wizard'
import { useBlitzStore } from './store/useBlitzStore'

function App() {
  const { runId } = useBlitzStore()
  const [inWizard, setInWizard] = useState(false)

  if (runId && inWizard) {
    return <Wizard />
  }

  return <Landing onLaunch={() => setInWizard(true)} />
}

export default App
