import { useState } from 'react'
import { useVoiceSession } from '../hooks/useVoiceSession'
import { API_BASE } from '../config'

/**
 * Standalone voice test page — bypasses the full pipeline.
 * Access via /?voice-test in the browser.
 */
export default function VoiceTest() {
  const voice = useVoiceSession()
  const [status, setStatus] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [scriptText, setScriptText] = useState(
    'Hi, I\'m calling from Acme Corp. We help companies automate their sales outreach. Do you have a few minutes to chat?'
  )
  const [firstMessage, setFirstMessage] = useState(
    'Hey! This is Alex from Acme Corp — do you have a quick minute?'
  )

  async function handleStart() {
    setError(null)
    setStatus('connecting')

    try {
      // First check setup
      const check = await fetch(`${API_BASE}/voice/setup-check`)
      const checkData = await check.json()
      if (!checkData.configured) {
        setError(`Missing env vars: ${checkData.missing.join(', ')}`)
        setStatus('error')
        return
      }

      // Start session with dummy run_id (backend handles missing research gracefully)
      const res = await fetch(`${API_BASE}/voice/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: 'voice-test-dummy',
          segment_name: 'Test Segment',
          script_text: scriptText,
          first_message: firstMessage,
        }),
      })

      if (!res.ok) {
        const detail = await res.text()
        setError(`Backend error ${res.status}: ${detail}`)
        setStatus('error')
        return
      }

      const data = await res.json()
      console.log('[VoiceTest] Session response:', data)

      setStatus('live')
      await voice.start(data.token)
    } catch (err) {
      setError(`Network error: ${err}`)
      setStatus('error')
    }
  }

  async function handleStop() {
    await voice.stop()
    setStatus('idle')
  }

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', fontFamily: 'system-ui', padding: 20 }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>Voice Agent Test Page</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>
        Bypasses the full pipeline. Tests ElevenLabs connection directly.
      </p>

      {/* Script input */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Sales Script</label>
        <textarea
          value={scriptText}
          onChange={(e) => setScriptText(e.target.value)}
          rows={4}
          style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #ccc', fontSize: 14 }}
          disabled={status === 'live'}
        />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>First Message (agent says this)</label>
        <input
          value={firstMessage}
          onChange={(e) => setFirstMessage(e.target.value)}
          style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #ccc', fontSize: 14 }}
          disabled={status === 'live'}
        />
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        {status !== 'live' ? (
          <button
            onClick={handleStart}
            disabled={status === 'connecting'}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: status === 'connecting' ? '#999' : '#22c55e', color: '#fff',
              fontWeight: 600, fontSize: 14,
            }}
          >
            {status === 'connecting' ? 'Connecting...' : 'Start Call'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: '#ef4444', color: '#fff', fontWeight: 600, fontSize: 14,
            }}
          >
            End Call
          </button>
        )}
      </div>

      {/* Status */}
      <div style={{ marginBottom: 16 }}>
        <strong>SDK Status:</strong> {voice.status} | <strong>Speaking:</strong> {voice.isSpeaking ? 'Yes' : 'No'} | <strong>ConvID:</strong> {voice.conversationId ?? 'none'}
      </div>

      {/* Error */}
      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>
          {error}
        </div>
      )}

      {/* Transcript */}
      <div>
        <h3 style={{ marginBottom: 8 }}>Live Transcript ({voice.transcript.length} messages)</h3>
        <div style={{
          border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, minHeight: 120,
          maxHeight: 300, overflowY: 'auto', background: '#f9fafb',
        }}>
          {voice.transcript.length === 0 && (
            <p style={{ color: '#999' }}>No messages yet...</p>
          )}
          {voice.transcript.map((entry, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <strong style={{ color: entry.role === 'agent' ? '#2563eb' : '#16a34a' }}>
                {entry.role === 'agent' ? 'Agent' : 'You'}:
              </strong>{' '}
              {entry.content}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
