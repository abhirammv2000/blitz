import { useState } from 'react'

interface ScriptPreviewProps {
  segmentName: string
  initialScript: string
  onConfirmCall: (phoneNumber: string, editedScript: string, firstMessage: string) => void
  onBack: () => void
}

export default function ScriptPreview({ segmentName, initialScript, onConfirmCall, onBack }: ScriptPreviewProps) {
  const [script, setScript] = useState(initialScript)
  const [firstMessage, setFirstMessage] = useState(
    "Hi, I'm Alex! I'm calling about [company] — we have something that could really help your team."
  )
  const [phoneNumber, setPhoneNumber] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)

  const canCall = phoneNumber.trim().length > 0

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <button
          onClick={onBack}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
        >
          <span>←</span> Back
        </button>
        <span className="text-xs text-zinc-600">/</span>
        <p className="text-sm font-semibold text-white">{segmentName}</p>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
          Sales Script (edit before calling)
        </label>
        <textarea
          value={script}
          onChange={(e) => setScript(e.target.value)}
          rows={8}
          className="w-full rounded-xl border border-white/10 bg-white/3 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500/50 focus:bg-white/5 transition-all resize-y leading-relaxed"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
          Opening Line
        </label>
        <input
          type="text"
          value={firstMessage}
          onChange={(e) => setFirstMessage(e.target.value)}
          className="w-full rounded-xl border border-white/10 bg-white/3 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500/50 focus:bg-white/5 transition-all"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-zinc-500 uppercase tracking-widest font-medium">
          Phone Number (E.164 format)
        </label>
        <input
          type="tel"
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(e.target.value)}
          placeholder="+1 555 123 4567"
          className="w-full rounded-xl border border-white/10 bg-white/3 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500/50 focus:bg-white/5 transition-all"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 rounded-xl border border-white/10 bg-white/3 text-sm text-zinc-400 hover:text-zinc-200 hover:border-white/20 transition-all"
        >
          Back
        </button>
        <button
          onClick={() => setShowConfirm(true)}
          disabled={!canCall}
          className={`px-6 py-2.5 rounded-xl text-sm font-semibold transition-all ${
            canCall
              ? 'bg-gradient-to-r from-blue-600 to-violet-600 text-white hover:from-blue-500 hover:to-violet-500 shadow-lg shadow-blue-500/20'
              : 'bg-white/5 text-zinc-600 cursor-not-allowed border border-white/8'
          }`}
        >
          Call Now
        </button>
      </div>

      {showConfirm && (
        <div className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-5 flex flex-col gap-4">
          <p className="text-sm text-amber-300 font-medium">Ready to dial</p>
          <p className="text-sm text-zinc-300 leading-relaxed">
            You're about to call{' '}
            <span className="font-semibold text-white">{phoneNumber}</span> as{' '}
            <span className="font-semibold text-white">{segmentName}</span>. The agent will use the
            script above. Confirm?
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowConfirm(false)}
              className="px-4 py-2 rounded-xl border border-white/10 bg-white/3 text-sm text-zinc-400 hover:text-zinc-200 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                setShowConfirm(false)
                onConfirmCall(phoneNumber, script, firstMessage)
              }}
              className="px-6 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 text-sm font-semibold text-white hover:from-blue-500 hover:to-violet-500 shadow-lg shadow-blue-500/20 transition-all"
            >
              Confirm & Dial
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
