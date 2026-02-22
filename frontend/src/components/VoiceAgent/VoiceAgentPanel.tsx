import { useState, useEffect, useRef } from 'react'
import SegmentCards from './SegmentCards'
import ScriptPreview from './ScriptPreview'
import TranscriptCard from './TranscriptCard'

interface Segment {
  name: string
  description: string
}

interface TranscriptMessage {
  role: string
  content: string
}

type Stage = 'select' | 'preview' | 'calling' | 'transcript'

interface VoiceAgentPanelProps {
  runId: string
  segments: Segment[]
  salesScripts: Record<string, string>
}

export default function VoiceAgentPanel({ runId, segments, salesScripts }: VoiceAgentPanelProps) {
  const [stage, setStage] = useState<Stage>('select')
  const [selectedSegment, setSelectedSegment] = useState<Segment | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [setupError, setSetupError] = useState(false)
  const [timedOut, setTimedOut] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollCountRef = useRef(0)

  // Stop polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  function startPolling(convId: string) {
    pollCountRef.current = 0
    pollRef.current = setInterval(async () => {
      pollCountRef.current += 1
      if (pollCountRef.current > 60) {
        clearInterval(pollRef.current!)
        setTimedOut(true)
        setStage('transcript')
        return
      }
      try {
        const res = await fetch(`/voice/transcript/${convId}`)
        if (!res.ok) return
        const data = await res.json()
        if (data.messages && data.messages.length > 0) {
          clearInterval(pollRef.current!)
          setTranscript(data.messages)
          setStage('transcript')
        }
      } catch {
        // keep polling on network hiccups
      }
    }, 5000)
  }

  async function handleConfirmCall(phoneNumber: string, editedScript: string, firstMessage: string) {
    setError(null)
    setSetupError(false)
    setStage('calling')

    try {
      const res = await fetch('/voice/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          to_number: phoneNumber,
          segment_name: selectedSegment?.name ?? '',
          script_text: editedScript,
          first_message: firstMessage,
        }),
      })

      if (res.status === 503) {
        setSetupError(true)
        setStage('preview')
        return
      }

      if (!res.ok) {
        const detail = await res.text()
        setError(`Call failed: ${detail}`)
        setStage('preview')
        return
      }

      const data = await res.json()
      const convId = data.conversation_id
      setConversationId(convId)
      if (convId) {
        startPolling(convId)
      } else {
        // No conversation_id — call placed but no transcript available
        setStage('transcript')
      }
    } catch (err) {
      setError('Network error — could not reach the backend. Please try again.')
      setStage('preview')
    }
  }

  function reset() {
    if (pollRef.current) clearInterval(pollRef.current)
    setStage('select')
    setSelectedSegment(null)
    setConversationId(null)
    setTranscript([])
    setError(null)
    setSetupError(false)
    setTimedOut(false)
    pollCountRef.current = 0
  }

  const currentScript = selectedSegment ? (salesScripts[selectedSegment.name] ?? '') : ''

  return (
    <div className="flex flex-col gap-6">
      {/* Setup error banner */}
      {setupError && (
        <div className="rounded-xl border border-error/25 bg-error/5 p-5 flex flex-col gap-2">
          <p className="text-sm font-semibold text-error">ElevenLabs voice agent is not configured</p>
          <p className="text-sm text-ink-muted leading-relaxed">
            Set the following variables in your <code className="text-ink bg-cream-dark px-1.5 py-0.5 rounded text-xs">.env</code> file:
          </p>
          <ul className="flex flex-col gap-1 mt-1">
            {['ELEVENLABS_API_KEY', 'ELEVENLABS_AGENT_ID', 'ELEVENLABS_PHONE_NUMBER_ID'].map((v) => (
              <li key={v} className="text-xs text-ink font-mono bg-cream-dark rounded px-2 py-1">
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* General error banner */}
      {error && !setupError && (
        <div className="rounded-xl border border-error/25 bg-error/5 p-4 flex items-start gap-3">
          <p className="text-sm text-error flex-1">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-xs text-ink-faint hover:text-ink-muted flex-shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Timed out notice */}
      {timedOut && stage === 'transcript' && (
        <div className="rounded-xl border border-gold-400/25 bg-gold-100/50 p-4">
          <p className="text-sm text-gold-600">Call timed out or was not answered.</p>
        </div>
      )}

      {stage === 'select' && (
        <SegmentCards
          segments={segments}
          selectedSegment={selectedSegment}
          onSelect={(seg) => {
            setSelectedSegment(seg)
            setStage('preview')
          }}
        />
      )}

      {stage === 'preview' && selectedSegment && (
        <ScriptPreview
          segmentName={selectedSegment.name}
          initialScript={currentScript}
          onConfirmCall={handleConfirmCall}
          onBack={() => setStage('select')}
        />
      )}

      {stage === 'calling' && (
        <TranscriptCard transcript={[]} status="in_progress" />
      )}

      {stage === 'transcript' && (
        <div className="flex flex-col gap-4">
          <TranscriptCard transcript={transcript} status="completed" />
          <button
            onClick={reset}
            className="self-start px-4 py-2 rounded-xl border border-ink/10 bg-cream-dark text-sm text-ink-muted hover:text-ink hover:border-ink/20 transition-all"
          >
            Make Another Call
          </button>
        </div>
      )}
    </div>
  )
}
