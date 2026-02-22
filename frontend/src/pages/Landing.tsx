import { useState } from 'react'
import { useBlitzStore } from '../store/useBlitzStore'

interface LandingProps {
  onLaunch: () => void
}

export default function Landing({ onLaunch }: LandingProps) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const { error, startPipeline } = useBlitzStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    // Start pipeline in the store (survives unmount)
    startPipeline(url.trim())
    // Navigate immediately so user sees progress timeline
    onLaunch()
  }

  return (
    <div className="min-h-screen bg-cream flex flex-col items-center justify-center px-4">
      {/* Subtle warm gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-teal-100/40 via-cream to-gold-100/30 pointer-events-none" />

      <div className="relative z-10 w-full max-w-2xl flex flex-col items-center gap-8">
        {/* Wordmark */}
        <div className="flex flex-col items-center gap-3">
          <h1 className="font-display text-8xl font-black tracking-tighter bg-gradient-to-r from-teal-700 to-gold-500 bg-clip-text text-transparent select-none">
            Blitz
          </h1>
          <p className="text-ink-muted text-lg font-medium tracking-wide">
            One URL. Complete marketing pipeline.
          </p>
        </div>

        {/* Feature chips */}
        <div className="flex flex-wrap gap-2 justify-center">
          {['Research', 'Profiling', 'Audience', 'Content', 'Sales', 'Ads'].map((label) => (
            <span
              key={label}
              className="px-3 py-1 rounded-full bg-cream-dark border border-ink/10 text-ink-muted text-xs font-medium"
            >
              {label}
            </span>
          ))}
        </div>

        {/* URL Input Form */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
          <div className="relative">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://yourcompany.com"
              className="w-full bg-white border border-ink/10 rounded-2xl px-6 py-5 text-ink text-lg placeholder-ink-faint outline-none focus:border-teal-600/60 focus:ring-2 focus:ring-teal-600/10 transition-all duration-200"
              disabled={loading}
              autoFocus
            />
          </div>

          {error && (
            <p className="text-error text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:bg-teal-800 disabled:opacity-50 text-white font-bold text-lg py-5 rounded-2xl transition-all duration-200 cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-3">
                <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Launching pipeline...
              </span>
            ) : (
              'Launch'
            )}
          </button>
        </form>

        {/* Footer note */}
        <p className="text-ink-faint text-sm">
          AI-powered. Human-approved at every step.
        </p>
      </div>
    </div>
  )
}
