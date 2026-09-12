import { useEffect, useState } from 'react'
import Landing from './pages/Landing'
import Wizard from './components/Wizard'
import VoiceTest from './pages/VoiceTest'
import Telemetry from './pages/Telemetry'
import { useBlitzStore } from './store/useBlitzStore'

function App() {
  const { runId, loadRun } = useBlitzStore()
  const [launched, setLaunched] = useState(false)

  // Quick access: /?voice-test to test voice agent in isolation
  const isVoiceTest = window.location.search.includes('voice-test')
  // /?telemetry - the AI cost and reliability dashboard
  const isTelemetry = window.location.search.includes('telemetry')
  // /?run=<run_id> - reopen a run that already exists in storage, so closing
  // the tab (or the server restarting) does not strand a finished run behind
  // a page nobody can get back to.
  const runIdFromUrl = new URLSearchParams(window.location.search).get('run')

  useEffect(() => {
    if (runIdFromUrl) {
      loadRun(runIdFromUrl)
    }
    // Only ever needs to run once, against whatever the URL held on load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  let page
  if (isTelemetry) {
    page = <Telemetry />
  } else if (isVoiceTest) {
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

  return <>{page}</>

}

export default App
