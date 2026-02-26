import { useState } from 'react'
import SegmentCards from './SegmentCards'
import ScriptPreview from './ScriptPreview'
import TranscriptCard from './TranscriptCard'
import { useVoiceSession } from '../../hooks/useVoiceSession'
import { API_BASE } from '../../config'

interface Segment {
  name: string
  description: string
}

type Stage = 'select' | 'preview' | 'live' | 'transcript'

interface VoiceAgentPanelProps {
  runId: string
  segments: Segment[]
  salesScripts: Record<string, string>
  companyName?: string
}

export default function VoiceAgentPanel({ runId, segments, salesScripts, companyName }: VoiceAgentPanelProps) {
  const [stage, setStage] = useState<Stage>('select')
  const [selectedSegment, setSelectedSegment] = useState<Segment | null>(null)
  const [finalTranscript, setFinalTranscript] = useState<{ role: string; content: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  const [setupError, setSetupError] = useState(false)

  const voiceSession = useVoiceSession()

  async function handleConfirmCall(editedScript: string, firstMessage: string) {
    setError(null)
    setSetupError(false)

    try {
      const res = await fetch(`${API_BASE}/voice/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          segment_name: selectedSegment?.name ?? '',
          script_text: editedScript,
          first_message: firstMessage,
        }),
      })

      if (res.status === 503) {
        setSetupError(true)
        return
      }

      if (!res.ok) {
        const detail = await res.text()
        setError(`Failed to start: ${detail}`)
        return
      }

      const data = await res.json()
      setStage('live')
      await voiceSession.start(data.token)
    } catch {
      setError('Network error — could not reach the backend. Please try again.')
    }
  }

  async function handleEndConversation() {
    await voiceSession.stop()
    setFinalTranscript([...voiceSession.transcript])
    setStage('transcript')
  }

  function reset() {
    setStage('select')
    setSelectedSegment(null)
    setFinalTranscript([])
    setError(null)
    setSetupError(false)
  }

  const currentScript = selectedSegment ? (salesScripts[selectedSegment.name] ?? '') : ''

  return (
    <div className="flex flex-col gap-6">
      {setupError && (
        <div className="rounded-xl border border-error/25 bg-error/5 p-5 flex flex-col gap-2">
          <p className="text-sm font-semibold text-error">ElevenLabs voice agent is not configured</p>
          <p className="text-sm text-ink-muted leading-relaxed">
            Set the following variables in your <code className="text-ink bg-cream-dark px-1.5 py-0.5 rounded text-xs">.env</code> file:
          </p>
          <ul className="flex flex-col gap-1 mt-1">
            {['ELEVENLABS_API_KEY', 'ELEVENLABS_AGENT_ID'].map((v) => (
              <li key={v} className="text-xs text-ink font-mono bg-cream-dark rounded px-2 py-1">
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

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
          companyName={companyName}
          onConfirmCall={handleConfirmCall}
          onBack={() => setStage('select')}
        />
      )}

      {stage === 'live' && (
        <TranscriptCard
          transcript={voiceSession.transcript}
          status="live"
          isSpeaking={voiceSession.isSpeaking}
          onEndConversation={handleEndConversation}
        />
      )}

      {stage === 'transcript' && (
        <div className="flex flex-col gap-4">
          <TranscriptCard transcript={finalTranscript} status="completed" />
          <button
            onClick={reset}
            className="self-start px-4 py-2 rounded-xl border border-ink/10 bg-cream-dark text-sm text-ink-muted hover:text-ink hover:border-ink/20 transition-all"
          >
            Start Another Conversation
          </button>
        </div>
      )}
    </div>
  )
}
