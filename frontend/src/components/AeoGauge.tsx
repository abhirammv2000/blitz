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
              <Cell fill="#27272a" />
            </Pie>
          </PieChart>
          {/* Centered score */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-black" style={{ color }}>
              {score.toFixed(1)}
            </span>
            <span className="text-zinc-500 text-xs">/ 10</span>
          </div>
        </div>
        <p className="text-zinc-400 text-sm font-medium">AEO Visibility Score</p>
      </div>

      {/* "Why this score?" expandable */}
      {reasoning && (
        <Disclosure>
          {({ open }) => (
            <div className="rounded-xl border border-white/8 bg-white/2 overflow-hidden">
              <Disclosure.Button className="w-full flex items-center justify-between px-4 py-3 text-sm text-zinc-400 hover:text-white transition-colors">
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
              <Disclosure.Panel className="px-4 pb-4 text-sm text-zinc-400 leading-relaxed">
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
            className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-white">{d.model}</span>
              {d.mentioned ? (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  Mentioned
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-red-400">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Not mentioned
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-zinc-800">
                <div
                  className="h-1.5 rounded-full"
                  style={{
                    width: `${d.confidence * 100}%`,
                    backgroundColor: scoreColor(d.confidence * 10),
                  }}
                />
              </div>
              <span className="text-xs text-zinc-500">{Math.round(d.confidence * 100)}%</span>
            </div>
            {d.quote && (
              <p className="text-xs text-zinc-500 italic line-clamp-2">"{d.quote}"</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
