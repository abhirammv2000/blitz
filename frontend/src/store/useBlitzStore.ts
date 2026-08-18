import { create } from 'zustand'
import { IS_DEMO_MODE } from '../demo/demoConfig'
import { API_BASE } from '../config'

export const OUTPUT_KEYS: Record<string, number> = {
  research_output: 0,
  profile_output: 1,
  audience_output: 2,
  content_output: 3,
  sales_output: 4,
  ads_output: 5,
}

export interface ResearchProgressStep {
  step: string
  status: 'pending' | 'running' | 'done'
}

interface BlitzStore {
  runId: string | null
  currentStep: number
  viewStep: number
  agentOutputs: Record<number, unknown>
  isRunning: boolean
  researchProgress: ResearchProgressStep[]
  error: string | null
  activeAgentId: string | null
  setRunId: (id: string) => void
  setStep: (step: number) => void
  setViewStep: (step: number) => void
  setAgentOutput: (step: number, output: unknown) => void
  setIsRunning: (running: boolean) => void
  addResearchProgress: (evt: { step: string; status: string }) => void
  clearResearchProgress: () => void
  setError: (err: string | null) => void
  setActiveAgentId: (id: string | null) => void
  startPipeline: (url: string) => Promise<void>
  reset: () => void
}

// ---------------------------------------------------------------------------
// Main State Store (Zustand)
// ---------------------------------------------------------------------------
// This store holds all the data for a pipeline run and handles the real-time
// connection to the backend. It's the central nervous system of the frontend.

export const useBlitzStore = create<BlitzStore>()((set) => ({
  runId: null,
  currentStep: 0,
  viewStep: 0,
  agentOutputs: {},
  isRunning: false,
  researchProgress: [],
  error: null,
  activeAgentId: null,
  setActiveAgentId: (id) => set({ activeAgentId: id }),
  setRunId: (id) => set({ runId: id }),
  setStep: (step) => set({ currentStep: step, viewStep: step }),
  setViewStep: (step) => set({ viewStep: step }),
  setAgentOutput: (step, output) =>
    set((state) => ({ agentOutputs: { ...state.agentOutputs, [step]: output } })),
  setIsRunning: (running) => set({ isRunning: running }),
  addResearchProgress: (evt) =>
    set((state) => {
      const existing = state.researchProgress.findIndex((s) => s.step === evt.step)
      const updated =
        existing >= 0
          ? state.researchProgress.map((s, i) =>
              i === existing ? { ...s, status: evt.status as ResearchProgressStep['status'] } : s
            )
          : [
              ...state.researchProgress,
              { step: evt.step, status: evt.status as ResearchProgressStep['status'] },
            ]
      return { researchProgress: updated }
    }),
  clearResearchProgress: () => set({ researchProgress: [] }),
  setError: (err) => set({ error: err }),
  startPipeline: async (url: string) => {
    // If we're in demo mode, skip the real backend and play pre-recorded data
    if (IS_DEMO_MODE) {
      const { startDemoPipeline } = await import('../demo/demoPlayer')
      await startDemoPipeline(url)
      return
    }
    
    // Reset state before starting a new run
    set({ error: null, isRunning: true, researchProgress: [] })
    
    try {
      // 1. Send the URL to the backend to kick off the pipeline
      const res = await fetch(`${API_BASE}/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      // 2. The backend responds with an open stream (Server-Sent Events)
      // We read this stream chunk-by-chunk as it arrives over the wire.
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break // Stream finished

        // Add the new chunk of text to our buffer
        buffer += decoder.decode(value, { stream: true })
        
        // SSE messages are separated by newlines. We split the buffer into individual
        // messages. If the last chunk is incomplete (doesn't end with a newline),
        // we keep it in the buffer for the next time we read.
        const parts = buffer.split('\n')
        buffer = parts.pop() ?? ''

        // 3. Process each complete message
        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          
          try {
            // Strip the "data: " prefix and parse the JSON payload
            const event = JSON.parse(line.slice(6))

            // The backend just started our run and gave us a unique ID
            if (event.type === 'init') {
              set({ runId: event.run_id })
            }

            if (event.type === 'progress') {
              const step = event.data?.step ?? event.step
              const status = event.data?.status ?? event.status
              if (step && status) {
                const s = useBlitzStore.getState()
                const existing = s.researchProgress.findIndex((p) => p.step === step)
                const updated =
                  existing >= 0
                    ? s.researchProgress.map((p, i) =>
                        i === existing ? { ...p, status: status as ResearchProgressStep['status'] } : p
                      )
                    : [...s.researchProgress, { step, status: status as ResearchProgressStep['status'] }]
                set({ researchProgress: updated })
              }
            }

            // The backend finished a major step (an agent completed its work).
            // This contains the actual data (like the brand profile or ad copy).
            if (event.type === 'state' && event.data) {
              for (const [key, step] of Object.entries(OUTPUT_KEYS)) {
                if (event.data[key] !== undefined) {
                  set((state) => ({
                    agentOutputs: { ...state.agentOutputs, [step]: event.data[key] },
                  }))
                }
              }
              // Track pipeline progress (don't auto-advance viewStep)
              if (event.data.current_step !== undefined) {
                const step = event.data.current_step as number
                const s = useBlitzStore.getState()
                if (step >= s.currentStep) {
                  set({ currentStep: step })
                }
              }
            }

            if (event.type === 'done') {
              set({ isRunning: false })
              return
            }

            if (event.type === 'error') {
              set({ error: event.message, isRunning: false })
              return
            }
          } catch {
            // ignore parse errors on partial chunks
          }
        }
      }

      // Stream ended — mark pipeline as complete
      set({ isRunning: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to connect to backend',
        isRunning: false,
      })
    }
  },
  reset: () =>
    set({ runId: null, currentStep: 0, viewStep: 0, agentOutputs: {}, isRunning: false, researchProgress: [], error: null, activeAgentId: null }),
}))
