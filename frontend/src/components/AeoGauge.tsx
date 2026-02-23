import { PieChart, Pie, Cell } from 'recharts'
import { Disclosure } from '@headlessui/react'

export interface AeoDetail {
  model: string
  mentioned: boolean
  confidence: number
  quote: string
  reasoning?: string
}

interface AeoGaugeProps {
  score: number
  details: AeoDetail[]
  reasoning?: string
}

function scoreColor(score: number): string {
  if (score >= 7) return '#22c55e'
  if (score >= 4) return '#f59e0b'
  return '#ef4444'
}

export default function AeoGauge({ score, details, reasoning }: AeoGaugeProps) {
  const color = scoreColor(score)
  const filled = score / 10
  const data = [
    { value: filled },
    { value: 1 - filled },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Donut gauge */}
      <div className="flex flex-col items-center gap-2">
        <div className="relative">
          <PieChart width={160} height={160}>
            <Pie
              data={data}
              cx={80}
              cy={80}
              innerRadius={52}
              outerRadius={72}
              startAngle={90}
              endAngle={-270}
              dataKey="value"
              strokeWidth={0}
            >
              <Cell fill={color} />
              <Cell fill="#e5e7eb" />
            </Pie>
          </PieChart>
          {/* Centered score */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-black" style={{ color }}>
              {score.toFixed(1)}
            </span>
            <span className="text-ink-faint text-xs">/ 10</span>
          </div>
        </div>
        <p className="text-ink-muted text-sm font-medium">AEO Visibility Score</p>
      </div>

      {/* "Why this score?" expandable */}
      {reasoning && (
        <Disclosure>
          {({ open }) => (
            <div className="rounded-xl border border-ink/10 bg-cream overflow-hidden">
              <Disclosure.Button className="w-full flex items-center justify-between px-4 py-3 text-sm text-ink-muted hover:text-ink transition-colors">
                <span>Why this score?</span>
                <svg
                  className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Disclosure.Button>
              <Disclosure.Panel className="px-4 pb-4 text-sm text-ink-muted leading-relaxed">
                {reasoning}
              </Disclosure.Panel>
            </div>
          )}
        </Disclosure>
      )}

      {/* Per-chatbot cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {details.map((d) => (
          <div
            key={d.model}
            className="rounded-xl border border-ink/10 bg-cream p-4 flex flex-col gap-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-ink">{d.model}</span>
              {d.mentioned ? (
                <span className="flex items-center gap-1 text-xs text-success">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  Mentioned
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-error">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Not mentioned
                </span>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[11px] text-ink-muted">
                {d.mentioned ? 'Confidence' : 'Brand awareness'}
              </span>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-ink/10">
                  <div
                    className="h-1.5 rounded-full"
                    style={{
                      width: `${d.confidence * 100}%`,
                      backgroundColor: scoreColor(d.confidence * 10),
                    }}
                  />
                </div>
                <span className="text-xs text-ink-faint">{Math.round(d.confidence * 100)}%</span>
              </div>
            </div>
            {d.quote && (
              <p className="text-xs text-ink-muted italic line-clamp-2">"{d.quote}"</p>
            )}
            {d.reasoning && (
              <Disclosure>
                {({ open }) => (
                  <>
                    <Disclosure.Button className="text-[11px] text-ink-faint hover:text-ink-muted transition-colors flex items-center gap-1 mt-1">
                      <span>{open ? 'Hide' : 'View'} raw response</span>
                      <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </Disclosure.Button>
                    <Disclosure.Panel className="mt-1 p-2 rounded-lg bg-ink/5 text-[11px] text-ink-muted leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                      {d.reasoning}
                    </Disclosure.Panel>
                  </>
                )}
              </Disclosure>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
