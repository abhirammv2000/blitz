import { useState } from 'react'
import Landing from './pages/Landing'
import Wizard from './components/Wizard'
import VoiceTest from './pages/VoiceTest'
import ElevenLabsWidget from './components/VoiceAgent/ElevenLabsWidget'
import { useBlitzStore } from './store/useBlitzStore'

function App() {
  const { runId, activeAgentId } = useBlitzStore()
  const [launched, setLaunched] = useState(false)

  // Quick access: /?voice-test to test voice agent in isolation
  const isVoiceTest = window.location.search.includes('voice-test')

  let page
  if (isVoiceTest) {
    page = <VoiceTest />
  } else if (launched || runId) {
    page = (
      <div className="bg-cream text-ink min-h-screen">
        <Wizard />
      </div>
    )
  } else {
    page = (
      <div className="bg-cream text-ink min-h-screen">
        <Landing onLaunch={() => setLaunched(true)} />
      </div>
    )
  }

  return (
    <>
      {page}
      {activeAgentId && <ElevenLabsWidget agentId={activeAgentId} />}
    </>
  )
}

export default App
