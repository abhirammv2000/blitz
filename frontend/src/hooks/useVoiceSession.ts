import { useConversation } from '@11labs/react'
import { useCallback, useRef, useState } from 'react'

export interface TranscriptEntry {
  role: 'agent' | 'user'
  content: string
}

export function useVoiceSession() {
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const transcriptRef = useRef<TranscriptEntry[]>([])

  const conversation = useConversation({
    onConnect: () => {
      console.log('[Voice] Connected to ElevenLabs')
    },
    onDisconnect: (details) => {
      console.log('[Voice] Disconnected:', details)
    },
    onMessage: (message) => {
      console.log('[Voice] Message:', message)
      const entry: TranscriptEntry = {
        role: message.source === 'ai' ? 'agent' : 'user',
        content: message.message,
      }
      transcriptRef.current = [...transcriptRef.current, entry]
      setTranscript(transcriptRef.current)
    },
    onError: (error) => {
      console.error('[Voice] Error:', error)
    },
    onModeChange: (mode) => {
      console.log('[Voice] Mode changed:', mode)
    },
  })

  const start = useCallback(async (token: string) => {
    transcriptRef.current = []
    setTranscript([])
    setConversationId(null)
    console.log('[Voice] Requesting mic access...')
    await navigator.mediaDevices.getUserMedia({ audio: true })
    console.log('[Voice] Mic access granted. Starting session with token:', token?.slice(0, 20) + '...')
    console.log('[Voice] Starting session (no client overrides)')
    const id = await conversation.startSession({
      conversationToken: token,
    })
    console.log('[Voice] Session started, conversationId:', id)
    if (id) setConversationId(id)
  }, [conversation])

  const stop = useCallback(async () => {
    await conversation.endSession()
  }, [conversation])

  return {
    start,
    stop,
    transcript,
    conversationId,
    status: conversation.status,
    isSpeaking: conversation.isSpeaking,
  }
}
