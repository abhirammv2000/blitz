import { useBlitzStore } from '../store/useBlitzStore'
import DossierView from './DossierView'
import ApprovalGate from './ApprovalGate'
import ProgressTimeline from './ProgressTimeline'
import type { ResearchOutput } from './DossierView'

interface AgentStepProps {
  stepIndex: number
  agentName: string
}

export default function AgentStep({ stepIndex, agentName }: AgentStepProps) {
  const { agentOutputs, researchProgress, isRunning, setStep, runId } = useBlitzStore()
  const output = agentOutputs[stepIndex]

  // Step 0: Research Scout — full dossier flow
  if (stepIndex === 0) {
    // While running with no output: show progress timeline
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 text-sm font-bold">
                1
              </span>
              <h2 className="text-2xl font-bold text-white">{agentName}</h2>
            </div>
            <p className="text-zinc-500 text-sm ml-11">Researching your company...</p>
          </div>

          <div className="rounded-2xl border border-white/8 bg-white/3 p-6">
            <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-4">
              Progress
            </p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    // Output arrived: show dossier + approval gate
    if (output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 text-sm font-bold">
                1
              </span>
              <h2 className="text-2xl font-bold text-white">{agentName}</h2>
            </div>
            <p className="text-zinc-500 text-sm ml-11">Company Intelligence Dossier ready</p>
          </div>

          <DossierView output={output as ResearchOutput} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(1)}
            />
          )}
        </div>
      )
    }

    // Not yet running (waiting for pipeline start)
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 text-sm font-bold">
              1
            </span>
            <h2 className="text-2xl font-bold text-white">{agentName}</h2>
          </div>
          <p className="text-zinc-500 text-sm ml-11">Waiting for pipeline...</p>
        </div>

        <div className="rounded-2xl border border-white/8 bg-white/3 p-6 min-h-[200px] flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-zinc-600">
            <div className="w-10 h-10 rounded-full border-2 border-zinc-700 border-dashed flex items-center justify-center">
              <span className="text-lg">...</span>
            </div>
            <p className="text-sm">Research will begin shortly</p>
          </div>
        </div>
      </div>
    )
  }

  // Steps 1-5: stub behavior (wired in later phases)
  return (
    <div className="flex flex-col gap-6">
      {/* Agent heading */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-full bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 text-sm font-bold">
            {stepIndex + 1}
          </span>
          <h2 className="text-2xl font-bold text-white">{agentName}</h2>
        </div>
        <p className="text-zinc-500 text-sm ml-11">Waiting for pipeline...</p>
      </div>

      {/* Output placeholder */}
      <div className="rounded-2xl border border-white/8 bg-white/3 p-6 min-h-[200px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-zinc-600">
          <div className="w-10 h-10 rounded-full border-2 border-zinc-700 border-dashed flex items-center justify-center">
            <span className="text-lg">...</span>
          </div>
          <p className="text-sm">Agent output will appear here</p>
        </div>
      </div>

      {/* Approval gate — stub buttons */}
      <div className="flex flex-col gap-3">
        <p className="text-xs text-zinc-600 uppercase tracking-widest font-medium">Review &amp; Approve</p>
        <div className="flex gap-3">
          <button
            disabled
            className="flex-1 py-3 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-emerald-500 font-semibold text-sm cursor-not-allowed opacity-50 transition-all"
          >
            Approve
          </button>
          <button
            disabled
            className="flex-1 py-3 rounded-xl bg-amber-600/10 border border-amber-500/20 text-amber-500 font-semibold text-sm cursor-not-allowed opacity-50 transition-all"
          >
            Edit
          </button>
          <button
            disabled
            className="flex-1 py-3 rounded-xl bg-red-600/10 border border-red-500/20 text-red-500 font-semibold text-sm cursor-not-allowed opacity-50 transition-all"
          >
            Reject
          </button>
          <button
            disabled
            className="flex-1 py-3 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 font-semibold text-sm cursor-not-allowed opacity-50 transition-all"
          >
            Override
          </button>
        </div>
      </div>
    </div>
  )
}
