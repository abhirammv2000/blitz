import { useState } from 'react'
import { apiFetch } from '../config'
import { IS_DEMO_MODE } from '../demo/demoConfig'

interface FeedbackBarProps {
  runId: string
  agent: string
}

type Vote = 1 | -1

// Remembers votes for the life of the tab, so switching between steps doesn't
// make a vote look like it was lost. The backend has the real record.
const votes = new Map<string, Vote>()

export default function FeedbackBar({ runId, agent }: FeedbackBarProps) {
  const key = `${runId}:${agent}`
  const [vote, setVote] = useState<Vote | null>(votes.get(key) ?? null)
  const [error, setError] = useState<string | null>(null)

  // The demo replays a saved run, so there is nothing real to rate.
  if (IS_DEMO_MODE) return null

  async function send(value: Vote) {
    const previous = vote
    setVote(value)
    setError(null)
    try {
      const res = await apiFetch('/feedback/rating', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, agent, value }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      votes.set(key, value)
    } catch {
      setVote(previous)
      setError('Could not save that. Try again.')
    }
  }

  const base = 'rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all'
  const idle = 'bg-cream-dark border-ink/10 text-ink-muted hover:text-ink'
  const on = 'bg-teal-100 border-teal-600/40 text-teal-700'

  return (
    <div className="flex items-center gap-3 border-t border-ink/10 pt-4">
      <p className="text-xs text-ink-faint">Was this useful?</p>
      <button type="button" aria-pressed={vote === 1} onClick={() => send(1)} className={`${base} ${vote === 1 ? on : idle}`}>
        Yes
      </button>
      <button type="button" aria-pressed={vote === -1} onClick={() => send(-1)} className={`${base} ${vote === -1 ? on : idle}`}>
        No
      </button>
      {error && <p className="text-xs text-error">{error}</p>}
    </div>
  )
}
