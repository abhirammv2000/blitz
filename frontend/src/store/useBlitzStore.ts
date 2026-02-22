import { create } from 'zustand'

export interface ResearchProgressStep {
  step: string
  status: 'pending' | 'running' | 'done'
}

interface BlitzStore {
  runId: string | null
  currentStep: number
  agentOutputs: Record<number, unknown>
  isRunning: boolean
  researchProgress: ResearchProgressStep[]
  setRunId: (id: string) => void
  setStep: (step: number) => void
  setAgentOutput: (step: number, output: unknown) => void
  setIsRunning: (running: boolean) => void
  addResearchProgress: (evt: { step: string; status: string }) => void
  clearResearchProgress: () => void
  reset: () => void
}

export const useBlitzStore = create<BlitzStore>()((set) => ({
  runId: null,
  currentStep: 0,
  agentOutputs: {},
  isRunning: false,
  researchProgress: [],
  setRunId: (id) => set({ runId: id }),
  setStep: (step) => set({ currentStep: step }),
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
  reset: () =>
    set({ runId: null, currentStep: 0, agentOutputs: {}, isRunning: false, researchProgress: [] }),
}))
