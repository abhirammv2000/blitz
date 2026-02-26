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
  setRunId: (id: string) => void
  setStep: (step: number) => void
  setViewStep: (step: number) => void
  setAgentOutput: (step: number, output: unknown) => void
  setIsRunning: (running: boolean) => void
  addResearchProgress: (evt: { step: string; status: string }) => void
  clearResearchProgress: () => void
  setError: (err: string | null) => void
  startPipeline: (url: string) => Promise<void>
  reset: () => void
}

export const useBlitzStore = create<BlitzStore>()((set) => ({
  runId: null,
  currentStep: 0,
  viewStep: 0,
  agentOutputs: {},
  isRunning: false,
  researchProgress: [],
  error: null,
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
    if (IS_DEMO_MODE) {
      const { startDemoPipeline } = await import('../demo/demoPlayer')
      await startDemoPipeline(url)
      return
    }
    set({ error: null, isRunning: true, researchProgress: [] })
    try {
      const res = await fetch(`${API_BASE}/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))

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

            if (event.type === 'state' && event.data) {
              for (const [key, step] of Object.entries(OUTPUT_KEYS)) {
                if (event.data[key] !== undefined) {
                  set((state) => ({
                    agentOutputs: { ...state.agentOutputs, [step]: event.data[key] },
                  }))
                }
              }
            }

            if (event.type === 'interrupted') {
              // Extract output from interrupt payload using dynamic step from backend
              const interruptData = event.data
              if (interruptData?.output !== undefined && interruptData?.step !== undefined) {
                const step = interruptData.step as number
                set((state) => ({
                  agentOutputs: { ...state.agentOutputs, [step]: interruptData.output },
                }))
              } else if (interruptData?.output !== undefined) {
                // Fallback: step 0 for backward compatibility
                set((state) => ({
                  agentOutputs: { ...state.agentOutputs, 0: interruptData.output },
                }))
              }
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
      // Process remaining buffer
      if (buffer.trim() && buffer.trim().startsWith('data: ')) {
        try {
          const event = JSON.parse(buffer.trim().slice(6))
          if (event.type === 'interrupted') {
            const interruptData = event.data
            if (interruptData?.output !== undefined && interruptData?.step !== undefined) {
              set((state) => ({
                agentOutputs: { ...state.agentOutputs, [interruptData.step as number]: interruptData.output },
              }))
            }
            set({ isRunning: false })
            return
          }
        } catch { /* ignore */ }
      }
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to connect to backend',
        isRunning: false,
      })
    }
  },
  reset: () =>
    set({ runId: null, currentStep: 0, viewStep: 0, agentOutputs: {}, isRunning: false, researchProgress: [], error: null }),
}))
