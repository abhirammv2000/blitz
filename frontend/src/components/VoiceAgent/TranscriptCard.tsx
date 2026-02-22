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
      <div className="rounded-xl border border-teal-600/20 bg-teal-100/50 p-6 flex flex-col items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl animate-pulse">📞</span>
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-semibold text-teal-700">Call in progress...</p>
            <p className="text-xs text-ink-muted">Polling for transcript every 5 seconds</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-teal-600 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (status === 'completed' && transcript.length === 0) {
    return (
      <div className="rounded-xl border border-ink/10 bg-cream p-6 flex flex-col items-center gap-2">
        <p className="text-sm text-ink-muted">No transcript available — the call may have been too short.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-ink/10 bg-white p-5 flex flex-col gap-3">
      <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">
        Call Transcript
      </p>
      <div className="flex flex-col gap-3">
        {transcript.map((msg, i) => {
          const isAgent = msg.role === 'agent'
          return (
            <div key={i} className={`flex flex-col gap-1 ${isAgent ? 'items-start' : 'items-end'}`}>
              <p className={`text-xs font-medium ${isAgent ? 'text-teal-700' : 'text-ink-muted'}`}>
                {isAgent ? 'Agent' : 'Caller'}
              </p>
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                  isAgent
                    ? 'bg-teal-100 border border-teal-600/15 text-ink'
                    : 'bg-cream-dark border border-ink/10 text-ink-muted'
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
