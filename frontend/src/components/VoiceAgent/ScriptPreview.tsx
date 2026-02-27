import { useState } from 'react'

interface ScriptPreviewProps {
  segmentName: string
  initialScript: string
  companyName?: string
  onConfirmCall: (editedScript: string, firstMessage: string) => void
  onBack: () => void
}

export default function ScriptPreview({ segmentName, initialScript, companyName, onConfirmCall, onBack }: ScriptPreviewProps) {
  const [script, setScript] = useState(initialScript)
  const name = companyName || 'our company'
  const [firstMessage, setFirstMessage] = useState(
    `Hi there! This is Ava from ${name}. I'd love to share how we've been helping companies like yours — it'll only take a minute. Do you have a moment?`
  )
  const [showConfirm, setShowConfirm] = useState(false)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <button
          onClick={onBack}
          className="text-xs text-ink-faint hover:text-ink-muted transition-colors flex items-center gap-1"
        >
          <span>←</span> Back
        </button>
        <span className="text-xs text-ink-faint">/</span>
        <p className="text-sm font-semibold text-ink">{segmentName}</p>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-ink-faint uppercase tracking-widest font-medium">
          Sales Script (edit before starting)
        </label>
        <textarea
          value={script}
          onChange={(e) => setScript(e.target.value)}
          rows={8}
          className="w-full rounded-xl border border-ink/10 bg-cream px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-teal-600/40 focus:ring-2 focus:ring-teal-600/10 transition-all resize-y leading-relaxed"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-ink-faint uppercase tracking-widest font-medium">
          Opening Line
        </label>
        <input
          type="text"
          value={firstMessage}
          onChange={(e) => setFirstMessage(e.target.value)}
          className="w-full rounded-xl border border-ink/10 bg-cream px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-teal-600/40 focus:ring-2 focus:ring-teal-600/10 transition-all"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 rounded-xl border border-ink/10 bg-cream-dark text-sm text-ink-muted hover:text-ink hover:border-ink/20 transition-all"
        >
          Back
        </button>
        <button
          onClick={() => setShowConfirm(true)}
          className="px-6 py-2.5 rounded-xl text-sm font-semibold transition-all bg-teal-600 hover:bg-teal-700 text-white shadow-sm"
        >
          Start Conversation
        </button>
      </div>

      {showConfirm && (
        <div className="rounded-xl border border-gold-400/25 bg-gold-100/50 p-5 flex flex-col gap-4">
          <p className="text-sm text-gold-600 font-medium">Ready to start</p>
          <p className="text-sm text-ink leading-relaxed">
            You're about to start a voice conversation as{' '}
            <span className="font-semibold text-ink">{segmentName}</span>. The agent will use the
            script above and your microphone. Confirm?
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowConfirm(false)}
              className="px-4 py-2 rounded-xl border border-ink/10 bg-white text-sm text-ink-muted hover:text-ink transition-all"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                setShowConfirm(false)
                onConfirmCall(script, firstMessage)
              }}
              className="px-6 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-sm font-semibold text-white shadow-sm transition-all"
            >
              Confirm & Start
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
