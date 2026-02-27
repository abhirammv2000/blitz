/**
 * demoPlayer.ts — cached demo mode replay engine
 *
 * When VITE_DEMO_MODE=cached is set, the app replays pre-cached fixture data
 * with realistic timing instead of calling the real backend. The experience
 * is visually indistinguishable from a live run.
 *
 * Usage: copy frontend/.env.demo to frontend/.env.local, then run `npm run dev`
 */

import { useBlitzStore } from '../store/useBlitzStore'

export { IS_DEMO_MODE } from './demoConfig'

const delay = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms))

interface ProgressEvent {
  step: string
  status: string
  delay_ms: number
}

interface DemoFixture {
  run_id: string
  progress_events: ProgressEvent[]
  research_output: unknown
  profile_output: unknown
  audience_output: unknown
  content_output: unknown
  sales_output: unknown
  ads_output: unknown
  research_output_delay_ms: number
  profile_output_delay_ms: number
  audience_output_delay_ms: number
  content_output_delay_ms: number
  sales_output_delay_ms: number
  ads_output_delay_ms: number
}

// Store the active fixture so advanceDemoPipeline can access it
let activeFixture: DemoFixture | null = null

async function replayProgressEvents(events: ProgressEvent[]): Promise<void> {
  const store = useBlitzStore.getState()
  for (const evt of events) {
    await delay(evt.delay_ms)
    store.addResearchProgress({ step: evt.step, status: evt.status })
  }
}

/**
 * startDemoPipeline replays a fixture file with realistic timing.
 *
 * The function pauses after delivering the first agent output (research)
 * so the ApprovalGate renders exactly as in a live run. Clicking Approve
 * calls advanceDemoPipeline to continue to the next agent output.
 */
export async function startDemoPipeline(url: string): Promise<void> {
  const fixture: DemoFixture = (await import('./blossom.json')).default as DemoFixture

  activeFixture = fixture

  const store = useBlitzStore.getState()
  store.setError(null)
  store.setIsRunning(true)
  store.clearResearchProgress()

  await delay(300)
  store.setRunId(fixture.run_id)

  // Replay research progress events
  await replayProgressEvents(fixture.progress_events)

  // Agent 0 — Research output (step 0)
  await delay(Math.max(fixture.research_output_delay_ms, 400))
  store.setAgentOutput(0, fixture.research_output)
  store.setIsRunning(false)
  // Pause — ApprovalGate will call advanceDemoPipeline(1) on Approve
}

/**
 * advanceDemoPipeline is called by ApprovalGate in demo mode.
 * It delivers the next agent output after a realistic delay, then pauses again.
 */
export async function advanceDemoPipeline(nextStep: number): Promise<void> {
  if (!activeFixture) return

  const fixture = activeFixture
  const store = useBlitzStore.getState()

  store.setIsRunning(true)
  store.clearResearchProgress()

  const outputMap: Record<number, { output: unknown; delayMs: number }> = {
    1: { output: fixture.profile_output, delayMs: fixture.profile_output_delay_ms },
    2: { output: fixture.audience_output, delayMs: fixture.audience_output_delay_ms },
    3: { output: fixture.content_output, delayMs: fixture.content_output_delay_ms },
    4: { output: fixture.sales_output, delayMs: fixture.sales_output_delay_ms },
    5: { output: fixture.ads_output, delayMs: fixture.ads_output_delay_ms },
  }

  const entry = outputMap[nextStep]
  if (!entry) {
    // All agents complete — pipeline done
    store.setIsRunning(false)
    return
  }

  await delay(Math.max(entry.delayMs, 800)) // minimum 800ms so progress feels real

  store.setAgentOutput(nextStep, entry.output)
  store.setIsRunning(false)
  // Pause — ApprovalGate will call advanceDemoPipeline(nextStep + 1) on next Approve
}
