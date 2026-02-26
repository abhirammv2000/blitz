import { useState } from 'react'
import Landing from './pages/Landing'
import Wizard from './components/Wizard'
import VoiceTest from './pages/VoiceTest'
import { useBlitzStore } from './store/useBlitzStore'

function App() {
  const { runId } = useBlitzStore()
  const [launched, setLaunched] = useState(false)

  // Quick access: /?voice-test to test voice agent in isolation
  if (window.location.search.includes('voice-test')) {
    return <VoiceTest />
  }

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
