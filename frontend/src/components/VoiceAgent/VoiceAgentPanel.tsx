import { useState, useCallback, useRef } from 'react'
import SegmentCards from './SegmentCards'
import ScriptPreview from './ScriptPreview'
import TranscriptCard from './TranscriptCard'
import LeadsTable from './LeadsTable'
import { useBlitzStore } from '../../store/useBlitzStore'
import { useVoiceSession } from '../../hooks/useVoiceSession'
import { API_BASE } from '../../config'

interface Segment {
  name: string
  description: string
}

type Stage = 'select' | 'preview' | 'live' | 'extracting' | 'transcript'

interface VoiceAgentPanelProps {
  runId: string
  segments: Segment[]
  salesScripts: Record<string, string>
  companyName?: string
}

export default function VoiceAgentPanel({ runId, segments, salesScripts, companyName }: VoiceAgentPanelProps) {
  const [stage, setStage] = useState<Stage>('select')
  const [selectedSegment, setSelectedSegment] = useState<Segment | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [setupError, setSetupError] = useState(false)
  const conversationIdRef = useRef<string | null>(null)
  const setActiveAgentId = useBlitzStore((s) => s.setActiveAgentId)

  const handleDisconnect = useCallback(async () => {
    setActiveAgentId(null)
    setStage('extracting')

    // Best-effort lead extraction
    try {
      await fetch(`${API_BASE}/voice/leads/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          conversation_id: conversationIdRef.current,
        }),
      })
    } catch {
      // Lead extraction is best-effort
    }

    setStage('transcript')
  }, [runId, setActiveAgentId])

  const voice = useVoiceSession(handleDisconnect)

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
      setActiveAgentId(data.agent_id)

      // Start voice session via @11labs/react SDK
      try {
        await voice.start(data.token)
        // Grab the conversation ID assigned by the SDK
        conversationIdRef.current = voice.conversationIdRef.current
        setStage('live')
      } catch (voiceErr) {
        setError(`Microphone or voice error: ${voiceErr}`)
        setActiveAgentId(null)
        return
      }
    } catch {
      setError('Network error — could not reach the backend. Please try again.')
    }
  }

  async function handleEndCall() {
    await voice.stop()
    // onDisconnect callback handles the rest
  }

  function reset() {
    setStage('select')
    setSelectedSegment(null)
    setActiveAgentId(null)
    conversationIdRef.current = null
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
            {['ELEVENLABS_API_KEY'].map((v) => (
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
        <div className="flex flex-col items-center gap-4 py-8">
          <div className="h-3 w-3 rounded-full bg-teal-500 animate-pulse" />
          <p className="text-sm text-ink-muted">
            {voice.isSpeaking ? 'Agent is speaking...' : 'Listening...'}
          </p>

          {/* Live transcript */}
          {voice.transcript.length > 0 && (
            <div className="w-full max-w-md max-h-48 overflow-y-auto rounded-xl border border-ink/10 bg-cream-dark p-4 flex flex-col gap-2">
              {voice.transcript.map((entry, i) => (
                <p key={i} className="text-sm">
                  <span className={entry.role === 'agent' ? 'text-teal-700 font-medium' : 'text-ink font-medium'}>
                    {entry.role === 'agent' ? 'Ava' : 'You'}:
                  </span>{' '}
                  <span className="text-ink-muted">{entry.content}</span>
                </p>
              ))}
            </div>
          )}

          <button
            onClick={handleEndCall}
            className="px-4 py-2 rounded-xl border border-ink/10 bg-cream-dark text-sm text-ink-muted hover:text-ink hover:border-ink/20 transition-all"
          >
            End Conversation
          </button>
        </div>
      )}

      {stage === 'extracting' && (
        <div className="flex flex-col items-center gap-3 py-8">
          <div className="h-6 w-6 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-ink-muted">Extracting lead data...</p>
        </div>
      )}

      {stage === 'transcript' && (
        <div className="flex flex-col gap-4">
          <TranscriptCard transcript={voice.transcript.map(e => ({ role: e.role, content: e.content }))} status="completed" />
          <LeadsTable runId={runId} />
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
