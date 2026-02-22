interface AgentStepProps {
  stepIndex: number
  agentName: string
}

export default function AgentStep({ stepIndex, agentName }: AgentStepProps) {
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

      {/* Approval gate — stub buttons (wired in Phase 2) */}
      <div className="flex flex-col gap-3">
        <p className="text-xs text-zinc-600 uppercase tracking-widest font-medium">Review & Approve</p>
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
