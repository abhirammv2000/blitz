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
      <div className="relative z-10 w-full max-w-xl flex flex-col items-center gap-10">
        {/* Wordmark */}
        <div className="flex flex-col items-center gap-4">
          <h1 className="font-display text-8xl font-black tracking-tight text-ink select-none">
            Blitz
          </h1>
          <p className="text-ink-muted text-base tracking-wide max-w-sm text-center leading-relaxed">
            Enter a URL. Get a complete marketing strategy: research, audience, content, sales, and ads. Reviewed by you at every step.
          </p>
        </div>

        {/* Agent steps */}
        <div className="flex flex-wrap gap-2 justify-center">
          {[
            { label: 'Research', num: '01' },
            { label: 'Profile', num: '02' },
            { label: 'Audience', num: '03' },
            { label: 'Content', num: '04' },
            { label: 'Sales', num: '05' },
            { label: 'Ads', num: '06' },
          ].map(({ label, num }) => (
            <span
              key={label}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cream-dark border border-ink/8 text-xs"
            >
              <span className="text-ink-faint font-mono">{num}</span>
              <span className="text-ink font-medium">{label}</span>
            </span>
          ))}
        </div>

        {/* URL Input Form */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yourcompany.com"
            className="w-full bg-white border border-ink/10 rounded-xl px-5 py-4 text-ink text-base placeholder-ink-faint outline-none focus:border-sage/60 focus:ring-2 focus:ring-sage/10 transition-all duration-200"
            disabled={loading}
            autoFocus
          />

          {error && (
            <p className="text-error text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="w-full bg-rust hover:bg-rust/90 disabled:opacity-40 text-white font-semibold text-base py-4 rounded-xl transition-all duration-150 cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-3">
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running...
              </span>
            ) : (
              'Launch pipeline'
            )}
          </button>
        </form>

        {/* Footer */}
        <p className="text-ink-faint text-xs tracking-wide">
          Six agents. Every output reviewed by you before moving on.
        </p>
      </div>
    </div>
  )
}
