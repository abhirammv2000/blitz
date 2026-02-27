import { useEffect, useRef } from 'react'
import '@elevenlabs/convai-widget-embed'

interface ElevenLabsWidgetProps {
  agentId: string
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'elevenlabs-convai': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & { 'agent-id'?: string; variant?: string },
        HTMLElement
      >
    }
  }
}

export default function ElevenLabsWidget({ agentId }: ElevenLabsWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Force re-mount when agentId changes
    const el = containerRef.current
    if (!el) return
    el.innerHTML = ''
    const widget = document.createElement('elevenlabs-convai')
    widget.setAttribute('agent-id', agentId)
    el.appendChild(widget)

    return () => {
      el.innerHTML = ''
    }
  }, [agentId])

  return <div ref={containerRef} className="fixed bottom-6 right-6 z-50" />
}
