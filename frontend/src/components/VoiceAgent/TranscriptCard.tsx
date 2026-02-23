interface TranscriptMessage {
  role: string
  content: string
}

interface TranscriptCardProps {
  transcript: TranscriptMessage[]
  status: string
  isSpeaking?: boolean
  onEndConversation?: () => void
}

export default function TranscriptCard({ transcript, status, isSpeaking, onEndConversation }: TranscriptCardProps) {
  if (status === 'live') {
    return (
      <div className="rounded-xl border border-teal-600/20 bg-teal-100/50 p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-2xl ${isSpeaking ? 'animate-pulse' : ''}`}>🎙️</span>
            <div className="flex flex-col gap-0.5">
              <p className="text-sm font-semibold text-teal-700">
                {isSpeaking ? 'Agent is speaking...' : 'Listening...'}
              </p>
              <p className="text-xs text-ink-muted">Live conversation in progress</p>
            </div>
          </div>
          {onEndConversation && (
            <button
              onClick={onEndConversation}
              className="px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 text-sm font-semibold text-white shadow-sm transition-all"
            >
              End Conversation
            </button>
          )}
        </div>

        {transcript.length > 0 && (
          <div className="flex flex-col gap-3 max-h-80 overflow-y-auto">
            {transcript.map((msg, i) => {
              const isAgent = msg.role === 'agent'
              return (
                <div key={i} className={`flex flex-col gap-1 ${isAgent ? 'items-start' : 'items-end'}`}>
                  <p className={`text-xs font-medium ${isAgent ? 'text-teal-700' : 'text-ink-muted'}`}>
                    {isAgent ? 'Agent' : 'You'}
                  </p>
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                      isAgent
                        ? 'bg-white/70 border border-teal-600/15 text-ink'
                        : 'bg-teal-600/10 border border-teal-600/15 text-ink'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  if (status === 'in_progress') {
    return (
      <div className="rounded-xl border border-teal-600/20 bg-teal-100/50 p-6 flex flex-col items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl animate-pulse">🎙️</span>
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-semibold text-teal-700">Connecting...</p>
            <p className="text-xs text-ink-muted">Setting up voice session</p>
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
        <p className="text-sm text-ink-muted">No transcript available — the conversation may have been too short.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-ink/10 bg-white p-5 flex flex-col gap-3">
      <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">
        Conversation Transcript
      </p>
      <div className="flex flex-col gap-3">
        {transcript.map((msg, i) => {
          const isAgent = msg.role === 'agent'
          return (
            <div key={i} className={`flex flex-col gap-1 ${isAgent ? 'items-start' : 'items-end'}`}>
              <p className={`text-xs font-medium ${isAgent ? 'text-teal-700' : 'text-ink-muted'}`}>
                {isAgent ? 'Agent' : 'You'}
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
