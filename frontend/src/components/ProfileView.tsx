import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'

// TypeScript interfaces matching backend Pydantic schemas
export interface BrandDNA {
  mission: string
  values: string[]
  tone: string
  visual_style: string
}

export interface MarketingGap {
  gap: string
  recommendation: string
}

export interface MarketingProfile {
  brand_dna: BrandDNA
  positioning_statement: string
  usps: string[]
  marketing_gaps: MarketingGap[]
}

interface ProfileViewProps {
  profile: MarketingProfile
}

export default function ProfileView({ profile }: ProfileViewProps) {
  const { brand_dna, positioning_statement, usps, marketing_gaps } = profile

  return (
    <div className="rounded-2xl border border-white/8 bg-white/3 overflow-hidden">
      <TabGroup>
        <TabList className="flex border-b border-white/8">
          {['Brand DNA', 'Positioning', 'USPs & Gaps'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 px-4 py-3 text-sm font-medium text-zinc-500 hover:text-zinc-300 data-[selected]:text-white data-[selected]:bg-white/5 data-[selected]:border-b-2 data-[selected]:border-violet-500 transition-colors outline-none"
            >
              {tab}
            </Tab>
          ))}
        </TabList>

        <TabPanels>
          {/* Brand DNA Tab */}
          <TabPanel className="p-6 flex flex-col gap-5">
            {/* Mission quote block */}
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-2">Mission</p>
              <blockquote className="border-l-2 border-blue-500 pl-4 italic text-zinc-300 text-sm leading-relaxed">
                {brand_dna.mission}
              </blockquote>
            </div>

            {/* Values tags */}
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-2">Values</p>
              <div className="flex flex-wrap gap-2">
                {brand_dna.values.map((value, i) => (
                  <span
                    key={i}
                    className="inline-flex rounded-full bg-white/8 px-3 py-1 text-xs text-zinc-300 font-medium"
                  >
                    {value}
                  </span>
                ))}
              </div>
            </div>

            {/* Tone badge */}
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-2">Tone</p>
              <span className="inline-flex rounded-full bg-violet-500/15 border border-violet-500/25 px-3 py-1 text-xs text-violet-300 font-medium">
                {brand_dna.tone}
              </span>
            </div>

            {/* Visual style */}
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-2">Visual Style</p>
              <p className="text-zinc-300 text-sm leading-relaxed">{brand_dna.visual_style}</p>
            </div>
          </TabPanel>

          {/* Positioning Tab */}
          <TabPanel className="p-6">
            <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-4">Positioning Statement</p>
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5">
              <p className="text-zinc-200 text-base leading-relaxed font-medium">{positioning_statement}</p>
            </div>
          </TabPanel>

          {/* USPs & Gaps Tab — SWOT-style grid */}
          <TabPanel className="p-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {/* Strengths (USPs) */}
              <div>
                <p className="text-xs text-emerald-400 uppercase tracking-widest font-medium mb-3">
                  Strengths / USPs
                </p>
                <div className="flex flex-col gap-2">
                  {usps.map((usp, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-emerald-500/15 bg-emerald-500/5 px-4 py-3 text-sm text-zinc-300 flex items-start gap-2"
                    >
                      <span className="text-emerald-400 font-bold flex-shrink-0 mt-0.5">+</span>
                      {usp}
                    </div>
                  ))}
                </div>
              </div>

              {/* Opportunities (Gaps) */}
              <div>
                <p className="text-xs text-amber-400 uppercase tracking-widest font-medium mb-3">
                  Opportunities / Gaps
                </p>
                <div className="flex flex-col gap-2">
                  {marketing_gaps.map((gap, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-amber-500/15 bg-amber-500/5 px-4 py-3 flex flex-col gap-1"
                    >
                      <p className="text-sm text-zinc-300 flex items-start gap-2">
                        <span className="text-amber-400 font-bold flex-shrink-0 mt-0.5">!</span>
                        {gap.gap}
                      </p>
                      <p className="text-xs text-zinc-500 leading-relaxed pl-4">{gap.recommendation}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  )
}
