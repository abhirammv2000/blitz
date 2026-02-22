import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'

// TypeScript interfaces matching backend Pydantic schemas
export interface EmailInSequence {
  step: number
  subject: string
  body: string
  delay_days: number
}

export interface EmailSequence {
  segment: string
  emails: EmailInSequence[]
}

export interface LinkedInTemplate {
  segment: string
  connection_request: string
  follow_up_1: string
  follow_up_2: string
}

export interface LeadTier {
  tier: string
  description: string
  signals: string[]
  action: string
}

export interface PipelineStage {
  stage: string
  definition: string
  entry_criteria: string
  exit_criteria: string
  actions: string[]
}

export interface SalesOutput {
  email_sequences: EmailSequence[]
  linkedin_templates: LinkedInTemplate[]
  lead_scoring: LeadTier[]
  pipeline_stages: PipelineStage[]
}

interface SalesViewProps {
  output: SalesOutput
}

const EMAIL_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'Insight', color: 'text-blue-700 bg-blue-500/10 border-blue-500/20' },
  2: { label: 'Value', color: 'text-teal-700 bg-teal-100 border-teal-600/20' },
  3: { label: 'Ask', color: 'text-success bg-success/10 border-success/20' },
}

const TIER_COLORS: Record<string, string> = {
  Hot: 'border-error/25 bg-error/5 text-error',
  Warm: 'border-gold-400/25 bg-gold-100/50 text-gold-600',
  Cold: 'border-blue-500/25 bg-blue-500/5 text-blue-700',
}

const PIPELINE_STAGE_COLORS = [
  'bg-cream-dark border-ink/10 text-ink',
  'bg-teal-100/50 border-teal-600/20 text-teal-700',
  'bg-gold-100/50 border-gold-400/20 text-gold-600',
  'bg-success/5 border-success/20 text-success',
]

export default function SalesView({ output }: SalesViewProps) {
  const {
    email_sequences = [],
    linkedin_templates = [],
    lead_scoring = [],
    pipeline_stages = [],
  } = output

  return (
    <div className="rounded-2xl border border-ink/10 bg-white overflow-hidden">
      <TabGroup>
        <TabList className="flex border-b border-ink/10 overflow-x-auto">
          {['Email Sequences', 'LinkedIn DMs', 'Lead Scoring', 'Pipeline'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 min-w-max px-4 py-3 text-sm font-medium text-ink-muted hover:text-ink data-[selected]:text-ink data-[selected]:bg-cream-dark data-[selected]:border-b-2 data-[selected]:border-teal-600 transition-colors outline-none"
            >
              {tab}
            </Tab>
          ))}
        </TabList>

        <TabPanels>
          {/* Email Sequences Tab */}
          <TabPanel className="p-6 flex flex-col gap-5">
            {email_sequences.length === 0 && (
              <p className="text-sm text-ink-faint italic">No email sequences generated.</p>
            )}
            {email_sequences.map((seq, i) => (
              <div key={i} className="flex flex-col gap-3">
                <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">
                  Segment: <span className="text-ink normal-case">{seq.segment}</span>
                </p>
                <div className="flex flex-col gap-2">
                  {(seq.emails ?? []).map((email, j) => {
                    const meta = EMAIL_LABELS[email.step] ?? { label: `Email ${email.step}`, color: 'text-ink-muted bg-cream-dark border-ink/10' }
                    return (
                      <div key={j} className="rounded-xl border border-ink/10 bg-cream p-4 flex flex-col gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${meta.color}`}>
                            Email {email.step}: {meta.label}
                          </span>
                          {email.delay_days !== undefined && (
                            <span className="inline-flex rounded-full bg-cream-dark border border-ink/10 px-2 py-0.5 text-xs text-ink-faint">
                              Day {email.delay_days}
                            </span>
                          )}
                        </div>
                        <p className="text-xs font-semibold text-ink">{email.subject}</p>
                        <p className="text-xs text-ink-muted leading-relaxed whitespace-pre-line">{email.body}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </TabPanel>

          {/* LinkedIn DMs Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {linkedin_templates.length === 0 && (
              <p className="text-sm text-ink-faint italic">No LinkedIn templates generated.</p>
            )}
            {linkedin_templates.map((tmpl, i) => (
              <div key={i} className="rounded-xl border border-ink/10 bg-cream p-4 flex flex-col gap-3">
                <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">
                  Segment: <span className="text-ink normal-case">{tmpl.segment}</span>
                </p>
                <div>
                  <p className="text-xs text-teal-700 uppercase tracking-widest font-medium mb-1">Connection Request</p>
                  <p className="text-xs text-ink leading-relaxed">{tmpl.connection_request}</p>
                </div>
                <div>
                  <p className="text-xs text-teal-700 uppercase tracking-widest font-medium mb-1">Follow-up 1</p>
                  <p className="text-xs text-ink leading-relaxed">{tmpl.follow_up_1}</p>
                </div>
                {tmpl.follow_up_2 && (
                  <div>
                    <p className="text-xs text-teal-700 uppercase tracking-widest font-medium mb-1">Follow-up 2</p>
                    <p className="text-xs text-ink leading-relaxed">{tmpl.follow_up_2}</p>
                  </div>
                )}
              </div>
            ))}
          </TabPanel>

          {/* Lead Scoring Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {lead_scoring.length === 0 && (
              <p className="text-sm text-ink-faint italic">No lead scoring tiers generated.</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {lead_scoring.map((tier, i) => {
                const colorClass = TIER_COLORS[tier.tier] ?? 'border-ink/10 bg-cream-dark text-ink'
                return (
                  <div key={i} className={`rounded-xl border p-4 flex flex-col gap-3 ${colorClass}`}>
                    <p className="text-sm font-bold">{tier.tier}</p>
                    <div>
                      <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1.5">Signals</p>
                      <ul className="flex flex-col gap-1">
                        {(tier.signals ?? []).map((signal, j) => (
                          <li key={j} className="text-xs text-ink-muted flex items-start gap-1.5">
                            <span className="flex-shrink-0 mt-0.5">·</span>
                            {signal}
                          </li>
                        ))}
                      </ul>
                    </div>
                    {tier.action && (
                      <div>
                        <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Action</p>
                        <p className="text-xs text-ink">{tier.action}</p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </TabPanel>

          {/* Pipeline Stages Tab */}
          <TabPanel className="p-6">
            {pipeline_stages.length === 0 && (
              <p className="text-sm text-ink-faint italic">No pipeline stages generated.</p>
            )}
            <div className="flex flex-col gap-3">
              {pipeline_stages.map((stage, i) => {
                const colorClass = PIPELINE_STAGE_COLORS[i % PIPELINE_STAGE_COLORS.length]
                return (
                  <div key={i} className={`rounded-xl border px-4 py-3 flex flex-col gap-1 ${colorClass}`}>
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-ink/10 flex items-center justify-center text-xs font-bold flex-shrink-0">
                        {i + 1}
                      </span>
                      <p className="text-sm font-semibold">{stage.stage}</p>
                    </div>
                    {stage.definition && (
                      <p className="text-xs text-ink-muted pl-7 leading-relaxed">{stage.definition}</p>
                    )}
                    {stage.entry_criteria && (
                      <p className="text-xs text-ink-faint pl-7">
                        Entry: <span className="text-ink">{stage.entry_criteria}</span>
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  )
}
