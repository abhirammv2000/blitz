interface TranscriptMessage {
  role: string
  content: string
}

interface TranscriptCardProps {
  transcript: TranscriptMessage[]
  status: string
}

export default function TranscriptCard({ transcript, status }: TranscriptCardProps) {
  if (status === 'in_progress') {
    return (
      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-6 flex flex-col items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl animate-pulse">📞</span>
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-semibold text-blue-300">Call in progress...</p>
            <p className="text-xs text-zinc-500">Polling for transcript every 5 seconds</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (status === 'completed' && transcript.length === 0) {
    return (
      <div className="rounded-xl border border-white/8 bg-white/3 p-6 flex flex-col items-center gap-2">
        <p className="text-sm text-zinc-500">No transcript available — the call may have been too short.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-white/8 bg-white/3 p-5 flex flex-col gap-3">
      <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
        Call Transcript
      </p>
      <div className="flex flex-col gap-3">
        {transcript.map((msg, i) => {
          const isAgent = msg.role === 'agent'
          return (
            <div key={i} className={`flex flex-col gap-1 ${isAgent ? 'items-start' : 'items-end'}`}>
              <p className={`text-xs font-medium ${isAgent ? 'text-blue-400' : 'text-zinc-500'}`}>
                {isAgent ? 'Agent' : 'Caller'}
              </p>
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                  isAgent
                    ? 'bg-blue-900/30 border border-blue-500/15 text-zinc-200'
                    : 'bg-zinc-800/60 border border-white/8 text-zinc-300'
                }`}
              >
                {msg.content}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
