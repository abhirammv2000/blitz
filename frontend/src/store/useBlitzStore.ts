import { create } from 'zustand'

interface BlitzStore {
  runId: string | null
  currentStep: number
  agentOutputs: Record<number, unknown>
  isRunning: boolean
  setRunId: (id: string) => void
  setStep: (step: number) => void
  setAgentOutput: (step: number, output: unknown) => void
  setIsRunning: (running: boolean) => void
  reset: () => void
}

export const useBlitzStore = create<BlitzStore>()((set) => ({
  runId: null,
  currentStep: 0,
  agentOutputs: {},
  isRunning: false,
  setRunId: (id) => set({ runId: id }),
  setStep: (step) => set({ currentStep: step }),
  setAgentOutput: (step, output) =>
    set((state) => ({ agentOutputs: { ...state.agentOutputs, [step]: output } })),
  setIsRunning: (running) => set({ isRunning: running }),
  reset: () => set({ runId: null, currentStep: 0, agentOutputs: {}, isRunning: false }),
}))
