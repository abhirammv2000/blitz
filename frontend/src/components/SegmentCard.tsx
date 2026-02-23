import { useState } from 'react'
import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'

// TypeScript interfaces matching backend Pydantic schemas
export interface AudienceSegmentDemographics {
  age_range?: string
  job_titles?: string[]
  company_sizes?: string[]
  industries?: string[]
}

export interface AudienceSegmentPsychographics {
  values?: string[]
  goals?: string[]
  frustrations?: string[]
  personality_traits?: string[]
}

export interface AudienceSegmentSyntheticAttributes {
  sample_job_title?: string
  tools_used?: string[]
  content_habits?: string
  estimated_salary_range?: string
  decision_timeline?: string
  [key: string]: unknown
}

export interface AudienceSegment {
  name: string
  demographics: AudienceSegmentDemographics
  psychographics: AudienceSegmentPsychographics
  pain_points: string[]
  buying_triggers: string[]
  active_channels: string[]
  reasoning: string
  fit_label: string // "High" | "Medium" | "Low"
  synthetic_attributes: AudienceSegmentSyntheticAttributes
}

interface SegmentCardProps {
  segment: AudienceSegment
  index: number
  onFlag?: (index: number, feedback: string) => void
}

function fitLabelStyles(label: string): string {
  switch (label) {
    case 'High':
      return 'bg-success/10 text-success border-success/30'
    case 'Medium':
      return 'bg-gold-100 text-gold-600 border-gold-400/30'
    case 'Low':
      return 'bg-error/10 text-error border-error/30'
    default:
      return 'bg-cream-dark text-ink-muted border-ink/10'
  }
}

function TagList({ items, className = '' }: { items: string[]; className?: string }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span
          key={i}
          className={`inline-flex rounded-full bg-cream-dark px-2 py-0.5 text-xs text-ink ${className}`}
        >
          {item}
        </span>
      ))}
    </div>
  )
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-1">
      {items.map((item, i) => (
        <li key={i} className="text-xs text-ink-muted flex items-start gap-1.5">
          <span className="text-teal-600 mt-0.5 flex-shrink-0">•</span>
          {item}
        </li>
      ))}
    </ul>
  )
}

export default function SegmentCard({ segment, index, onFlag }: SegmentCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [flagging, setFlagging] = useState(false)
  const [flagText, setFlagText] = useState('')

  const handleFlag = () => {
    if (onFlag) {
      onFlag(index, flagText)
    }
    setFlagging(false)
    setFlagText('')
  }

  const demos = segment.demographics
  const psychos = segment.psychographics
  const synth = segment.synthetic_attributes

  return (
    <div className="flex-shrink-0 w-80 rounded-2xl border border-ink/10 bg-white p-5 flex flex-col gap-4">
      {/* Header: name + fit label badge */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-bold text-ink leading-snug">{segment.name}</h3>
        <span
          className={`inline-flex flex-shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold ${fitLabelStyles(segment.fit_label)}`}
        >
          {segment.fit_label}
        </span>
      </div>

      {/* Mini-tabs */}
      <TabGroup>
        <TabList className="flex rounded-xl bg-cream-dark p-0.5 gap-0.5">
          {['Demo', 'Psycho', 'Triggers', 'Channels'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 rounded-lg px-1.5 py-1 text-xs font-medium text-ink-muted hover:text-ink data-[selected]:bg-white data-[selected]:text-ink data-[selected]:shadow-sm transition-all outline-none"
            >
              {tab}
            </Tab>
          ))}
        </TabList>

        <TabPanels>
          {/* Demographics */}
          <TabPanel className="flex flex-col gap-2 pt-2">
            {demos.age_range && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Age</p>
                <p className="text-xs text-ink">{demos.age_range}</p>
              </div>
            )}
            {demos.job_titles && demos.job_titles.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Job Titles</p>
                <TagList items={demos.job_titles} />
              </div>
            )}
            {demos.company_sizes && demos.company_sizes.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Company Size</p>
                <TagList items={demos.company_sizes} />
              </div>
            )}
            {demos.industries && demos.industries.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Industries</p>
                <TagList items={demos.industries} />
              </div>
            )}
          </TabPanel>

          {/* Psychographics */}
          <TabPanel className="flex flex-col gap-2 pt-2">
            {psychos.values && psychos.values.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Values</p>
                <TagList items={psychos.values} />
              </div>
            )}
            {psychos.goals && psychos.goals.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Goals</p>
                <BulletList items={psychos.goals} />
              </div>
            )}
            {psychos.frustrations && psychos.frustrations.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Frustrations</p>
                <BulletList items={psychos.frustrations} />
              </div>
            )}
            {psychos.personality_traits && psychos.personality_traits.length > 0 && (
              <div>
                <p className="text-xs text-ink-faint mb-1">Traits</p>
                <TagList items={psychos.personality_traits} />
              </div>
            )}
          </TabPanel>

          {/* Triggers */}
          <TabPanel className="pt-2">
            <BulletList items={segment.buying_triggers} />
          </TabPanel>

          {/* Channels */}
          <TabPanel className="pt-2">
            <TagList items={segment.active_channels} />
          </TabPanel>
        </TabPanels>
      </TabGroup>

      {/* Citation-style reasoning — always visible */}
      <div className="rounded-xl border border-ink/8 bg-cream px-3 py-2.5">
        <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Reasoning</p>
        <p className="text-xs text-ink-muted leading-relaxed italic">{segment.reasoning}</p>
      </div>

      {/* Expandable synthetic attributes */}
      <div>
        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="flex items-center gap-1.5 text-xs text-ink-faint hover:text-ink-muted transition-colors"
        >
          <svg
            className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Synthetic Attributes
        </button>

        {expanded && synth && (
          <div className="mt-2 flex flex-col gap-1.5 rounded-xl border border-ink/8 bg-cream-dark px-3 py-2.5">
            {Object.entries(synth).map(([key, value]) => {
              if (value == null) return null
              const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
              if (Array.isArray(value) && value.length > 0) {
                return (
                  <div key={key}>
                    <span className="text-xs text-ink-faint">{label}</span>
                    <TagList items={value.map(String)} className="mt-1" />
                  </div>
                )
              }
              return (
                <div key={key} className="flex justify-between gap-2">
                  <span className="text-xs text-ink-faint flex-shrink-0">{label}</span>
                  <span className="text-xs text-ink text-right">{String(value)}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Per-segment approve/flag affordance */}
      {!flagging ? (
        <div className="flex gap-2 mt-auto pt-1 border-t border-ink/8">
          <button
            className="flex-1 py-1.5 rounded-lg text-xs font-medium text-success hover:bg-success/10 transition-all"
            title="Looks good"
          >
            ✓ Approve
          </button>
          <button
            onClick={() => setFlagging(true)}
            className="flex-1 py-1.5 rounded-lg text-xs font-medium text-gold-600 hover:bg-gold-100 transition-all"
            title="Flag for review"
          >
            ⚑ Flag
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2 mt-auto pt-1 border-t border-ink/8">
          <textarea
            value={flagText}
            onChange={(e) => setFlagText(e.target.value)}
            placeholder="What's wrong with this segment?"
            rows={2}
            className="rounded-lg border border-gold-400/20 bg-gold-100/50 px-2.5 py-2 text-xs text-ink placeholder-ink-faint outline-none focus:border-gold-400/40 resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={handleFlag}
              className="flex-1 py-1.5 rounded-lg text-xs font-medium text-gold-600 bg-gold-100 hover:bg-gold-100/80 transition-all"
            >
              Submit
            </button>
            <button
              onClick={() => setFlagging(false)}
              className="px-3 py-1.5 rounded-lg text-xs text-ink-muted hover:bg-cream-dark transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
