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
    <div className="rounded-2xl border border-ink/10 bg-white overflow-hidden">
      <TabGroup>
        <TabList className="flex border-b border-ink/10">
          {['Brand DNA', 'Positioning', 'USPs & Gaps'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 px-4 py-3 text-sm font-medium text-ink-muted hover:text-ink data-[selected]:text-ink data-[selected]:bg-cream-dark data-[selected]:border-b-2 data-[selected]:border-teal-600 transition-colors outline-none"
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
              <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-2">Mission</p>
              <blockquote className="border-l-2 border-teal-600 pl-4 italic text-ink-muted text-sm leading-relaxed">
                {brand_dna.mission}
              </blockquote>
            </div>

            {/* Values tags */}
            <div>
              <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-2">Values</p>
              <div className="flex flex-wrap gap-2">
                {brand_dna.values.map((value, i) => (
                  <span
                    key={i}
                    className="inline-flex rounded-full bg-cream-dark px-3 py-1 text-xs text-ink font-medium"
                  >
                    {value}
                  </span>
                ))}
              </div>
            </div>

            {/* Tone badge */}
            <div>
              <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-2">Tone</p>
              <span className="inline-flex rounded-full bg-teal-100 border border-teal-600/25 px-3 py-1 text-xs text-teal-700 font-medium">
                {brand_dna.tone}
              </span>
            </div>

            {/* Visual style */}
            <div>
              <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-2">Visual Style</p>
              <p className="text-ink-muted text-sm leading-relaxed">{brand_dna.visual_style}</p>
            </div>
          </TabPanel>

          {/* Positioning Tab */}
          <TabPanel className="p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Positioning Statement</p>
            <div className="rounded-xl border border-teal-600/20 bg-teal-100/50 p-5">
              <p className="text-ink text-base leading-relaxed font-medium">{positioning_statement}</p>
            </div>
          </TabPanel>

          {/* USPs & Gaps Tab — SWOT-style grid */}
          <TabPanel className="p-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {/* Strengths (USPs) */}
              <div>
                <p className="text-xs text-success uppercase tracking-widest font-medium mb-3">
                  Strengths / USPs
                </p>
                <div className="flex flex-col gap-2">
                  {usps.map((usp, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-success/15 bg-success/5 px-4 py-3 text-sm text-ink flex items-start gap-2"
                    >
                      <span className="text-success font-bold flex-shrink-0 mt-0.5">+</span>
                      {usp}
                    </div>
                  ))}
                </div>
              </div>

              {/* Opportunities (Gaps) */}
              <div>
                <p className="text-xs text-gold-600 uppercase tracking-widest font-medium mb-3">
                  Opportunities / Gaps
                </p>
                <div className="flex flex-col gap-2">
                  {marketing_gaps.map((gap, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-gold-400/20 bg-gold-100/50 px-4 py-3 flex flex-col gap-1"
                    >
                      <p className="text-sm text-ink flex items-start gap-2">
                        <span className="text-gold-600 font-bold flex-shrink-0 mt-0.5">!</span>
                        {gap.gap}
                      </p>
                      <p className="text-xs text-ink-muted leading-relaxed pl-4">{gap.recommendation}</p>
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
