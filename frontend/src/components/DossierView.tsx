import { useState } from 'react'
import { Disclosure } from '@headlessui/react'
import AeoGauge from './AeoGauge'
import type { AeoDetail } from './AeoGauge'

export interface ResearchOutput {
  company_name: string
  company_url: string
  summary: string
  executive_summary: string
  press_coverage: Array<{ title: string; url: string; snippet: string }>
  site_content: string
  competitors: Array<{ name: string; positioning: string; strengths: string[]; weaknesses: string[] }>
  aeo_score: number
  aeo_details: AeoDetail[]
}

interface DossierViewProps {
  output: ResearchOutput
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-5 h-5 text-zinc-500 transition-transform ${open ? 'rotate-180' : ''}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  )
}

const PANELS = ['press', 'competitors', 'aeo'] as const
type PanelId = typeof PANELS[number]

export default function DossierView({ output }: DossierViewProps) {
  const [openPanel, setOpenPanel] = useState<PanelId | null>('press')

  const toggle = (panel: PanelId) => {
    setOpenPanel((prev) => (prev === panel ? null : panel))
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Executive summary */}
      <div className="rounded-2xl border border-white/8 bg-white/3 p-5">
        <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-2">
          {output.company_name}
        </p>
        <p className="text-zinc-300 text-sm leading-relaxed">{output.executive_summary}</p>
      </div>

      {/* Press Coverage */}
      <div className="rounded-2xl border border-white/8 overflow-hidden">
        <button
          onClick={() => toggle('press')}
          className="w-full flex items-center justify-between px-5 py-4 bg-white/3 hover:bg-white/5 transition-colors"
        >
          <span className="text-sm font-semibold text-white">Press Coverage</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-600">{output.press_coverage.length} articles</span>
            <ChevronIcon open={openPanel === 'press'} />
          </div>
        </button>
        {openPanel === 'press' && (
          <div className="px-5 py-4 flex flex-col gap-4 bg-black/20">
            {output.press_coverage.length === 0 && (
              <p className="text-zinc-600 text-sm italic">No press coverage found.</p>
            )}
            {output.press_coverage.map((article, i) => (
              <div key={i} className="flex flex-col gap-1">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-violet-400 hover:text-violet-300 transition-colors leading-snug"
                >
                  {article.title}
                </a>
                <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">{article.snippet}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Competitor Analysis */}
      <div className="rounded-2xl border border-white/8 overflow-hidden">
        <button
          onClick={() => toggle('competitors')}
          className="w-full flex items-center justify-between px-5 py-4 bg-white/3 hover:bg-white/5 transition-colors"
        >
          <span className="text-sm font-semibold text-white">Competitor Analysis</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-600">{output.competitors.length} competitors</span>
            <ChevronIcon open={openPanel === 'competitors'} />
          </div>
        </button>
        {openPanel === 'competitors' && (
          <div className="px-5 py-4 bg-black/20">
            {output.competitors.length === 0 && (
              <p className="text-zinc-600 text-sm italic">No competitor data found.</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {output.competitors.map((comp, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3"
                >
                  <p className="text-sm font-bold text-white">{comp.name}</p>
                  <p className="text-xs text-zinc-400 leading-relaxed italic">{comp.positioning}</p>
                  {comp.strengths?.length > 0 && (
                    <div>
                      <p className="text-xs text-emerald-400 font-semibold uppercase tracking-wider mb-1">
                        Strengths
                      </p>
                      <ul className="flex flex-col gap-0.5">
                        {comp.strengths.map((s, j) => (
                          <li key={j} className="text-xs text-zinc-400 flex items-start gap-1.5">
                            <span className="text-emerald-500 mt-0.5 flex-shrink-0">+</span>
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {comp.weaknesses?.length > 0 && (
                    <div>
                      <p className="text-xs text-red-400 font-semibold uppercase tracking-wider mb-1">
                        Weaknesses
                      </p>
                      <ul className="flex flex-col gap-0.5">
                        {comp.weaknesses.map((w, j) => (
                          <li key={j} className="text-xs text-zinc-400 flex items-start gap-1.5">
                            <span className="text-red-500 mt-0.5 flex-shrink-0">-</span>
                            {w}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* AEO Visibility */}
      <div className="rounded-2xl border border-white/8 overflow-hidden">
        <button
          onClick={() => toggle('aeo')}
          className="w-full flex items-center justify-between px-5 py-4 bg-white/3 hover:bg-white/5 transition-colors"
        >
          <span className="text-sm font-semibold text-white">AEO Visibility</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-600">Score: {output.aeo_score.toFixed(1)}/10</span>
            <ChevronIcon open={openPanel === 'aeo'} />
          </div>
        </button>
        {openPanel === 'aeo' && (
          <div className="px-5 py-6 bg-black/20">
            <AeoGauge score={output.aeo_score} details={output.aeo_details} />
          </div>
        )}
      </div>
    </div>
  )
}
