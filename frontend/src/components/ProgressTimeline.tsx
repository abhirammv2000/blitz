import type { ResearchProgressStep } from '../store/useBlitzStore'

const STEP_LABELS: Record<string, string> = {
  tavily: 'Tavily Search',
  firecrawl: 'Website Crawl',
  aeo: 'AEO Scoring',
  dossier: 'Dossier Assembly',
  // fallback: step ID itself
}

function StatusIcon({ status }: { status: ResearchProgressStep['status'] }) {
  if (status === 'running') {
    return (
      <span className="inline-block w-5 h-5 border-2 border-violet-400/40 border-t-violet-400 rounded-full animate-spin flex-shrink-0" />
    )
  }
  if (status === 'done') {
    return (
      <span className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </span>
    )
  }
  // pending
  return (
    <span className="w-5 h-5 rounded-full border-2 border-zinc-700 bg-white/3 flex-shrink-0" />
  )
}

interface ProgressTimelineProps {
  steps: ResearchProgressStep[]
}

export default function ProgressTimeline({ steps }: ProgressTimelineProps) {
  return (
    <div className="flex flex-col gap-0 py-4">
      {steps.map((s, i) => (
        <div key={s.step} className="flex items-start gap-3">
          {/* Dot + connector */}
          <div className="flex flex-col items-center">
            <StatusIcon status={s.status} />
            {i < steps.length - 1 && (
              <div className="w-px flex-1 min-h-[24px] bg-zinc-800 my-1" />
            )}
          </div>
          {/* Label */}
          <p
            className={`text-sm pt-0.5 pb-6 font-medium ${
              s.status === 'done'
                ? 'text-zinc-400'
                : s.status === 'running'
                ? 'text-violet-300'
                : 'text-zinc-600'
            }`}
          >
            {STEP_LABELS[s.step] ?? s.step}
          </p>
        </div>
      ))}

      {steps.length === 0 && (
        <p className="text-zinc-600 text-sm italic">Waiting for pipeline to start...</p>
      )}
    </div>
  )
}
