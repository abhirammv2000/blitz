import { useState, useRef } from 'react'
import { useBlitzStore } from '../store/useBlitzStore'

type Mode = 'idle' | 'edit' | 'reject' | 'override'

const REJECT_REASONS = [
  'Too generic',
  'Missing info',
  'Wrong focus',
  'Inaccurate data',
  'Needs more depth',
]

interface ApprovalGateProps {
  output: unknown
  runId: string
  onDecisionComplete: () => void
}

async function readSSEStream(
  stream: ReadableStream<Uint8Array>,
  onProgress: (step: string, status: string) => void,
  onOutput: (data: unknown) => void,
  onDone: () => void
) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      for (const line of text.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'progress') {
            onProgress(event.data?.step ?? event.step, event.data?.status ?? event.status)
          }
          if (event.type === 'state' && event.data?.research_output) {
            onOutput(event.data.research_output)
          }
          if (event.type === 'interrupted') {
            onDone()
          }
        } catch {
          // ignore parse errors
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export default function ApprovalGate({ output, runId, onDecisionComplete }: ApprovalGateProps) {
  const [mode, setMode] = useState<Mode>('idle')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedReasons, setSelectedReasons] = useState<string[]>([])
  const [rejectText, setRejectText] = useState('')
  const [overrideText, setOverrideText] = useState(() =>
    JSON.stringify(output, null, 2)
  )
  const editRef = useRef<HTMLPreElement>(null)
  const { addResearchProgress, clearResearchProgress, setAgentOutput, setIsRunning } =
    useBlitzStore()

  const postDecision = async (decision: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`http://localhost:8000/pipeline/${runId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      })
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`)
      }
      return res
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
      setLoading(false)
      return null
    }
  }

  const handleApprove = async () => {
    const res = await postDecision({ action: 'approve' })
    if (!res) return
    onDecisionComplete()
    setLoading(false)
  }

  const handleEdit = async () => {
    // Collect edited content from the contenteditable ref
    const editedText = editRef.current?.innerText ?? ''
    let editedData: unknown
    try {
      editedData = JSON.parse(editedText)
    } catch {
      editedData = { text: editedText }
    }
    const res = await postDecision({ action: 'edit', data: editedData })
    if (!res) return
    onDecisionComplete()
    setLoading(false)
  }

  const handleReject = async () => {
    const combined = [...selectedReasons, rejectText].filter(Boolean).join('; ')
    const res = await postDecision({ action: 'reject', feedback: combined })
    if (!res || !res.body) return

    // Reject triggers re-generation — listen to SSE stream
    clearResearchProgress()
    setIsRunning(true)
    setMode('idle')

    await readSSEStream(
      res.body,
      (step, status) => addResearchProgress({ step, status }),
      (data) => setAgentOutput(0, data),
      () => setIsRunning(false)
    )
    setLoading(false)
  }

  const handleOverride = async () => {
    let parsedData: unknown
    try {
      parsedData = JSON.parse(overrideText)
    } catch {
      setError('Invalid JSON in override field.')
      setLoading(false)
      return
    }
    const res = await postDecision({ action: 'override', data: parsedData })
    if (!res) return
    onDecisionComplete()
    setLoading(false)
  }

  const toggleReason = (r: string) => {
    setSelectedReasons((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
    )
  }

  return (
    <div className="flex flex-col gap-4 mt-6">
      <p className="text-xs text-zinc-600 uppercase tracking-widest font-medium">
        Review &amp; Approve
      </p>

      {error && (
        <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      {/* IDLE: four action buttons */}
      {mode === 'idle' && (
        <div className="flex gap-3">
          <button
            onClick={handleApprove}
            disabled={loading}
            className="flex-1 py-3 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-emerald-500 font-semibold text-sm hover:bg-emerald-600/20 hover:border-emerald-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? '...' : 'Approve'}
          </button>
          <button
            onClick={() => setMode('edit')}
            disabled={loading}
            className="flex-1 py-3 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 font-semibold text-sm hover:bg-blue-600/20 hover:border-blue-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Edit
          </button>
          <button
            onClick={() => setMode('reject')}
            disabled={loading}
            className="flex-1 py-3 rounded-xl bg-red-600/10 border border-red-500/20 text-red-500 font-semibold text-sm hover:bg-red-600/20 hover:border-red-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Reject
          </button>
          <button
            onClick={() => setMode('override')}
            disabled={loading}
            className="flex-1 py-3 rounded-xl bg-zinc-600/10 border border-zinc-500/20 text-zinc-400 font-semibold text-sm hover:bg-zinc-600/20 hover:border-zinc-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Override
          </button>
        </div>
      )}

      {/* EDIT mode */}
      {mode === 'edit' && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-zinc-500">
            Edit the JSON below inline, then save.
          </p>
          <pre
            ref={editRef}
            contentEditable
            suppressContentEditableWarning
            className="rounded-xl border border-blue-500/30 bg-blue-500/5 p-4 text-xs text-zinc-300 font-mono overflow-auto max-h-96 outline-none focus:border-blue-400/60 whitespace-pre-wrap"
          >
            {JSON.stringify(output, null, 2)}
          </pre>
          <div className="flex gap-3">
            <button
              onClick={handleEdit}
              disabled={loading}
              className="flex-1 py-3 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-300 font-semibold text-sm hover:bg-blue-600/30 disabled:opacity-50 transition-all"
            >
              {loading ? 'Saving...' : 'Save Edits'}
            </button>
            <button
              onClick={() => setMode('idle')}
              disabled={loading}
              className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-500 font-semibold text-sm hover:bg-white/3 transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* REJECT mode */}
      {mode === 'reject' && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-zinc-500">Select reasons and/or add details:</p>
          <div className="flex flex-wrap gap-2">
            {REJECT_REASONS.map((r) => (
              <button
                key={r}
                onClick={() => toggleReason(r)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  selectedReasons.includes(r)
                    ? 'bg-red-500/20 border-red-500/40 text-red-300'
                    : 'bg-white/3 border-white/10 text-zinc-400 hover:border-white/20'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <textarea
            value={rejectText}
            onChange={(e) => setRejectText(e.target.value)}
            placeholder="Additional feedback..."
            rows={3}
            className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-zinc-300 placeholder-zinc-600 outline-none focus:border-red-400/40 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={handleReject}
              disabled={loading || (selectedReasons.length === 0 && !rejectText.trim())}
              className="flex-1 py-3 rounded-xl bg-red-600/20 border border-red-500/30 text-red-300 font-semibold text-sm hover:bg-red-600/30 disabled:opacity-50 transition-all"
            >
              {loading ? 'Submitting...' : 'Submit Feedback'}
            </button>
            <button
              onClick={() => setMode('idle')}
              disabled={loading}
              className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-500 font-semibold text-sm hover:bg-white/3 transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* OVERRIDE mode */}
      {mode === 'override' && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-zinc-500">
            Paste or type replacement JSON (must match dossier schema):
          </p>
          <textarea
            value={overrideText}
            onChange={(e) => setOverrideText(e.target.value)}
            rows={14}
            className="rounded-xl border border-zinc-600/30 bg-zinc-900/50 px-4 py-3 text-xs text-zinc-300 font-mono outline-none focus:border-zinc-500/50 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={handleOverride}
              disabled={loading}
              className="flex-1 py-3 rounded-xl bg-zinc-600/20 border border-zinc-500/30 text-zinc-300 font-semibold text-sm hover:bg-zinc-600/30 disabled:opacity-50 transition-all"
            >
              {loading ? 'Applying...' : 'Apply Override'}
            </button>
            <button
              onClick={() => setMode('idle')}
              disabled={loading}
              className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-500 font-semibold text-sm hover:bg-white/3 transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
