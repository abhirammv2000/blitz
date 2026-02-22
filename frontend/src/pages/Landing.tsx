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
    <div className="min-h-screen bg-black flex flex-col items-center justify-center px-4">
      {/* Background gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-violet-950/20 via-black to-indigo-950/20 pointer-events-none" />

      <div className="relative z-10 w-full max-w-2xl flex flex-col items-center gap-8">
        {/* Wordmark */}
        <div className="flex flex-col items-center gap-3">
          <h1 className="text-8xl font-black tracking-tighter bg-gradient-to-r from-violet-400 via-fuchsia-400 to-indigo-400 bg-clip-text text-transparent select-none">
            Blitz
          </h1>
          <p className="text-zinc-400 text-lg font-medium tracking-wide">
            One URL. Complete marketing pipeline.
          </p>
        </div>

        {/* Feature chips */}
        <div className="flex flex-wrap gap-2 justify-center">
          {['Research', 'Profiling', 'Audience', 'Content', 'Sales', 'Ads'].map((label) => (
            <span
              key={label}
              className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-zinc-400 text-xs font-medium"
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
              className="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-5 text-white text-lg placeholder-zinc-600 outline-none focus:border-violet-500/60 focus:bg-white/8 transition-all duration-200"
              disabled={loading}
              autoFocus
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:from-violet-900 disabled:to-indigo-900 disabled:opacity-50 text-white font-bold text-lg py-5 rounded-2xl transition-all duration-200 cursor-pointer disabled:cursor-not-allowed"
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
        <p className="text-zinc-600 text-sm">
          AI-powered. Human-approved at every step.
        </p>
      </div>
    </div>
  )
}
