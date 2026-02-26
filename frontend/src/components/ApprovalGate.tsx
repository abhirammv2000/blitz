import { useState, useRef } from 'react'
import { useBlitzStore, OUTPUT_KEYS } from '../store/useBlitzStore'
import { IS_DEMO_MODE } from '../demo/demoConfig'
import { API_BASE } from '../config'

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
  agentStep?: number
  agentOutputKey?: string
  summaryStats?: string
}

function processSSELine(
  line: string,
  onProgress: (step: string, status: string) => void,
  onOutput: (data: unknown) => void,
  onDone: () => void,
  outputKey: string,
) {
  if (!line.startsWith('data: ')) return
  try {
    const event = JSON.parse(line.slice(6))
    if (event.type === 'progress') {
      onProgress(event.data?.step ?? event.step, event.data?.status ?? event.status)
    }
    if (event.type === 'state' && event.data && outputKey) {
      if (event.data[outputKey] !== undefined) {
        onOutput(event.data[outputKey])
      }
    }
    if (event.type === 'interrupted') {
      if (event.data?.output !== undefined) {
        onOutput(event.data.output)
      }
      onDone()
    }
  } catch {
    // ignore parse errors on malformed events
  }
}

async function readSSEStream(
  stream: ReadableStream<Uint8Array>,
  onProgress: (step: string, status: string) => void,
  onOutput: (data: unknown) => void,
  onDone: () => void,
  outputKey: string = 'research_output'
) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE events are delimited by double newlines; process complete lines
      const parts = buffer.split('\n')
      // Keep the last part as it may be incomplete
      buffer = parts.pop() ?? ''

      for (const line of parts) {
        const trimmed = line.trim()
        if (trimmed) {
          processSSELine(trimmed, onProgress, onOutput, onDone, outputKey)
        }
      }
    }
    // Process any remaining buffer
    if (buffer.trim()) {
      processSSELine(buffer.trim(), onProgress, onOutput, onDone, outputKey)
    }
  } finally {
    reader.releaseLock()
  }
}

export default function ApprovalGate({
  output,
  runId,
  onDecisionComplete,
  agentStep = 0,
  agentOutputKey = 'research_output',
  summaryStats,
}: ApprovalGateProps) {
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
      const res = await fetch(`${API_BASE}/pipeline/${runId}/resume`, {
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
    if (IS_DEMO_MODE) {
      clearResearchProgress()
      onDecisionComplete()
      const { advanceDemoPipeline } = await import('../demo/demoPlayer')
      await advanceDemoPipeline(agentStep + 1)
      return
    }

    const res = await postDecision({ action: 'approve' })
    if (!res) return

    if (res.body) {
      setIsRunning(true)
      clearResearchProgress()
      onDecisionComplete()

      const nextOutputKey = Object.entries(OUTPUT_KEYS)
          .find(([, v]) => v === agentStep + 1)?.[0] ?? 'research_output'
      await readSSEStream(
        res.body,
        (step, status) => addResearchProgress({ step, status }),
        (data) => setAgentOutput(agentStep + 1, data),
        () => setIsRunning(false),
        nextOutputKey
      )
    } else {
      onDecisionComplete()
    }
    setLoading(false)
  }

  const handleEdit = async () => {
    const editedText = editRef.current?.innerText ?? ''
    let editedData: unknown
    try {
      editedData = JSON.parse(editedText)
    } catch {
      editedData = { text: editedText }
    }
    const res = await postDecision({ action: 'edit', data: editedData })
    if (!res) return

    if (res.body) {
      setIsRunning(true)
      clearResearchProgress()
      onDecisionComplete()

      await readSSEStream(
        res.body,
        (step, status) => addResearchProgress({ step, status }),
        (data) => setAgentOutput(agentStep + 1, data),
        () => setIsRunning(false),
        Object.entries(OUTPUT_KEYS)
          .find(([, v]) => v === agentStep + 1)?.[0] ?? 'research_output'
      )
    } else {
      onDecisionComplete()
    }
    setLoading(false)
  }

  const handleReject = async () => {
    if (IS_DEMO_MODE) {
      // In demo mode, reject re-shows the same output (no re-generation)
      setMode('idle')
      setSelectedReasons([])
      setRejectText('')
      return
    }

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
      (data) => setAgentOutput(agentStep, data),
      () => setIsRunning(false),
      agentOutputKey
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

    if (res.body) {
      setIsRunning(true)
      clearResearchProgress()
      onDecisionComplete()

      await readSSEStream(
        res.body,
        (step, status) => addResearchProgress({ step, status }),
        (data) => setAgentOutput(agentStep + 1, data),
        () => setIsRunning(false),
        Object.entries(OUTPUT_KEYS)
          .find(([, v]) => v === agentStep + 1)?.[0] ?? 'research_output'
      )
    } else {
      onDecisionComplete()
    }
    setLoading(false)
  }

  const toggleReason = (r: string) => {
    setSelectedReasons((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
    )
  }

  return (
    <div className="flex flex-col gap-4 mt-6 rounded-2xl border border-teal-600/20 ring-2 ring-teal-600/10 bg-white p-6">
      <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">
        Review &amp; Approve
      </p>

      {error && (
        <p className="text-error text-sm bg-error/5 border border-error/20 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      {/* IDLE: four action buttons */}
      {mode === 'idle' && (
        <div className="flex flex-col gap-3">
          {summaryStats && (
            <p className="text-xs text-ink-muted border border-ink/10 rounded-xl px-4 py-2 bg-cream mb-3">
              {summaryStats}
            </p>
          )}
          <div className="flex gap-3">
            <button
              onClick={handleApprove}
              disabled={loading}
              className="flex-1 py-3.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              {loading ? '...' : 'Approve'}
            </button>
            <button
              onClick={() => setMode('edit')}
              disabled={loading}
              className="flex-1 py-3.5 rounded-xl bg-gold-100 text-gold-600 border border-gold-400/30 hover:bg-gold-100/80 font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Edit
            </button>
            <button
              onClick={() => setMode('reject')}
              disabled={loading}
              className="flex-1 py-3.5 rounded-xl bg-error/10 text-error border border-error/30 hover:bg-error/20 font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Reject
            </button>
            <button
              onClick={() => setMode('override')}
              disabled={loading}
              className="flex-1 py-3.5 rounded-xl bg-ink/5 text-ink-muted border border-ink/10 hover:bg-ink/10 font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Override
            </button>
          </div>
        </div>
      )}

      {/* EDIT mode */}
      {mode === 'edit' && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-ink-muted">
            Edit the JSON below inline, then save.
          </p>
          <pre
            ref={editRef}
            contentEditable
            suppressContentEditableWarning
            className="rounded-xl border border-gold-400/30 bg-gold-100/50 p-4 text-xs text-ink font-mono overflow-auto max-h-96 outline-none focus:border-gold-500/60 whitespace-pre-wrap"
          >
            {JSON.stringify(output, null, 2)}
          </pre>
          <div className="flex gap-3">
            <button
              onClick={handleEdit}
              disabled={loading}
              className="flex-1 py-3 rounded-xl bg-gold-500 hover:bg-gold-600 text-white font-semibold text-sm disabled:opacity-50 transition-all"
            >
              {loading ? 'Saving...' : 'Save Edits'}
            </button>
            <button
              onClick={() => setMode('idle')}
              disabled={loading}
              className="px-6 py-3 rounded-xl border border-ink/10 text-ink-muted font-semibold text-sm hover:bg-cream-dark transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* REJECT mode */}
      {mode === 'reject' && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-ink-muted">Select reasons and/or add details:</p>
          <div className="flex flex-wrap gap-2">
            {REJECT_REASONS.map((r) => (
              <button
                key={r}
                onClick={() => toggleReason(r)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  selectedReasons.includes(r)
                    ? 'bg-error/10 border-error/40 text-error'
                    : 'bg-cream-dark border-ink/10 text-ink-muted hover:border-ink/20'
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
            className="rounded-xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-ink placeholder-ink-faint outline-none focus:border-error/40 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={handleReject}
              disabled={loading || (selectedReasons.length === 0 && !rejectText.trim())}
              className="flex-1 py-3 rounded-xl bg-error/10 border border-error/30 text-error font-semibold text-sm hover:bg-error/20 disabled:opacity-50 transition-all"
            >
              {loading ? 'Submitting...' : 'Submit Feedback'}
            </button>
            <button
              onClick={() => setMode('idle')}
              disabled={loading}
              className="px-6 py-3 rounded-xl border border-ink/10 text-ink-muted font-semibold text-sm hover:bg-cream-dark transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* OVERRIDE mode */}
      {mode === 'override' && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-ink-muted">
            Paste or type replacement JSON (must match dossier schema):
          </p>
          <textarea
            value={overrideText}
            onChange={(e) => setOverrideText(e.target.value)}
            rows={14}
            className="rounded-xl border border-ink/15 bg-cream-dark px-4 py-3 text-xs text-ink font-mono outline-none focus:border-ink/30 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={handleOverride}
              disabled={loading}
              className="flex-1 py-3 rounded-xl bg-ink/5 border border-ink/15 text-ink font-semibold text-sm hover:bg-ink/10 disabled:opacity-50 transition-all"
            >
              {loading ? 'Applying...' : 'Apply Override'}
            </button>
            <button
              onClick={() => setMode('idle')}
              disabled={loading}
              className="px-6 py-3 rounded-xl border border-ink/10 text-ink-muted font-semibold text-sm hover:bg-cream-dark transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
