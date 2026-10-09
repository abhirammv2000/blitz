import { useState } from 'react'
import { apiFetch } from '../config'
import { IS_DEMO_MODE } from '../demo/demoConfig'

interface AdPickProps {
  runId: string
  adCopyRef: string
  // The variant currently on screen, which is the one this button would pick.
  label: string
}

// Remembered for the life of the tab, so toggling variants doesn't make a
// pick look lost. The backend has the real record.
const picks = new Map<string, string>()

export default function AdPick({ runId, adCopyRef, label }: AdPickProps) {
  const key = `${runId}:${adCopyRef}`
  const [picked, setPicked] = useState<string | null>(picks.get(key) ?? null)
  const [error, setError] = useState<string | null>(null)

  // The demo replays a saved run, so there is nothing real to pick between.
  if (IS_DEMO_MODE) return null

  async function pick() {
    const previous = picked
    setPicked(label)
    setError(null)
    try {
      const res = await apiFetch('/feedback/ad-pick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, ad_copy_ref: adCopyRef, chosen: label }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      picks.set(key, label)
    } catch {
      setPicked(previous)
      setError('Could not save that. Try again.')
    }
  }

  const isPicked = picked === label
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={pick}
        disabled={isPicked}
        className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all ${
          isPicked
            ? 'bg-teal-100 border-teal-600/40 text-teal-700 cursor-default'
            : 'bg-cream-dark border-ink/10 text-ink-muted hover:text-ink'
        }`}
      >
        {isPicked ? `You picked Variant ${label}` : `Pick Variant ${label} as the better ad`}
      </button>
      {picked && !isPicked && <p className="text-xs text-ink-faint">Currently picked: Variant {picked}</p>}
      {error && <p className="text-xs text-error">{error}</p>}
    </div>
  )
}
