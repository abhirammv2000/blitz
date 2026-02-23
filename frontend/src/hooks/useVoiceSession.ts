import { useConversation } from '@11labs/react'
import { useCallback, useRef, useState } from 'react'

export interface TranscriptEntry {
  role: 'agent' | 'user'
  content: string
}

export function useVoiceSession() {
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const transcriptRef = useRef<TranscriptEntry[]>([])

  const conversation = useConversation({
    onMessage: (message) => {
      const entry: TranscriptEntry = {
        role: message.source === 'ai' ? 'agent' : 'user',
        content: message.message,
      }
      transcriptRef.current = [...transcriptRef.current, entry]
      setTranscript(transcriptRef.current)
    },
    onError: (error) => {
      console.error('Voice session error:', error)
    },
  })

  const start = useCallback(async (signedUrl: string) => {
    transcriptRef.current = []
    setTranscript([])
    await navigator.mediaDevices.getUserMedia({ audio: true })
    await conversation.startSession({ signedUrl })
  }, [conversation])

  const stop = useCallback(async () => {
    await conversation.endSession()
  }, [conversation])

  return {
    start,
    stop,
    transcript,
    status: conversation.status,
    isSpeaking: conversation.isSpeaking,
  }
}
