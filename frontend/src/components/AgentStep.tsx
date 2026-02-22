import { useBlitzStore } from '../store/useBlitzStore'
import DossierView from './DossierView'
import ProfileView from './ProfileView'
import AudienceView from './AudienceView'
import ContentView from './ContentView'
import SalesView from './SalesView'
import AdsView from './AdsView'
import ApprovalGate from './ApprovalGate'
import ProgressTimeline from './ProgressTimeline'
import VoiceAgentPanel from './VoiceAgent/VoiceAgentPanel'
import type { ResearchOutput } from './DossierView'
import type { MarketingProfile } from './ProfileView'
import type { AudienceOutput } from './AudienceView'
import type { ContentOutput } from './ContentView'
import type { SalesOutput } from './SalesView'
import type { AdsOutput } from './AdsView'

interface AgentStepProps {
  stepIndex: number
  agentName: string
}

function StepBadge({ number }: { number: number | string }) {
  return (
    <span className="w-8 h-8 rounded-full bg-teal-100 border border-teal-600/30 flex items-center justify-center text-teal-700 text-sm font-bold flex-shrink-0">
      {number}
    </span>
  )
}

export default function AgentStep({ stepIndex, agentName }: AgentStepProps) {
  const { agentOutputs, researchProgress, isRunning, setStep, runId } = useBlitzStore()
  const output = agentOutputs[stepIndex]

  // Step 0: Research Scout — full dossier flow
  if (stepIndex === 0) {
    // While running with no output: show progress timeline
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={1} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Researching your company...</p>
          </div>

          <div className="rounded-2xl border border-ink/10 bg-white p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">
              Progress
            </p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    // Output arrived: show dossier + approval gate
    if (output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={1} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Company Intelligence Dossier ready</p>
          </div>

          <DossierView output={output as ResearchOutput} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(1)}
            />
          )}
        </div>
      )
    }

    // Not yet running (waiting for pipeline start)
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <StepBadge number={1} />
            <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
          </div>
          <p className="text-ink-muted text-sm ml-11">Waiting for pipeline...</p>
        </div>

        <div className="rounded-2xl border border-ink/10 bg-white p-6 min-h-[200px] flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-ink-faint">
            <div className="w-10 h-10 rounded-full border-2 border-ink/20 border-dashed flex items-center justify-center">
              <span className="text-lg">...</span>
            </div>
            <p className="text-sm">Research will begin shortly</p>
          </div>
        </div>
      </div>
    )
  }

  // Step 1: Marketing Profile
  if (stepIndex === 1) {
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={2} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Synthesizing marketing profile...</p>
          </div>
          <div className="rounded-2xl border border-ink/10 bg-white p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Progress</p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    if (output) {
      const profile = output as MarketingProfile
      const uspCount = profile.usps?.length ?? 0
      const gapCount = profile.marketing_gaps?.length ?? 0
      const summaryStats = `Brand DNA synthesized — ${uspCount} USP${uspCount !== 1 ? 's' : ''} identified, ${gapCount} gap${gapCount !== 1 ? 's' : ''} found`

      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={2} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Marketing Profile ready</p>
          </div>

          <ProfileView profile={profile} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(2)}
              agentStep={1}
              agentOutputKey="profile_output"
              summaryStats={summaryStats}
            />
          )}
        </div>
      )
    }
  }

  // Step 2: Audience Segments
  if (stepIndex === 2) {
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={3} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Generating audience segments...</p>
          </div>
          <div className="rounded-2xl border border-ink/10 bg-white p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Progress</p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    if (output) {
      const audienceOutput = output as AudienceOutput
      const segCount = audienceOutput.segments?.length ?? 0
      const highFitCount = audienceOutput.segments?.filter((s) => s.fit_label === 'High').length ?? 0
      const summaryStats = `${segCount} segment${segCount !== 1 ? 's' : ''} generated, ${highFitCount} high-fit`

      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={3} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Audience Segments ready</p>
          </div>

          <AudienceView output={audienceOutput} runId={runId ?? ''} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(3)}
              agentStep={2}
              agentOutputKey="audience_output"
              summaryStats={summaryStats}
            />
          )}
        </div>
      )
    }
  }

  // Step 3: Content Strategist
  if (stepIndex === 3) {
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={4} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Generating content strategy...</p>
          </div>
          <div className="rounded-2xl border border-ink/10 bg-white p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Progress</p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    if (output) {
      const contentOutput = output as ContentOutput
      const postCount = contentOutput.social_posts?.length ?? 0
      const emailCount = contentOutput.email_campaigns?.length ?? 0
      const summaryStats = `${postCount} social post${postCount !== 1 ? 's' : ''} generated, ${emailCount} email campaign${emailCount !== 1 ? 's' : ''}`

      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={4} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Content Strategy ready</p>
          </div>

          <ContentView output={contentOutput} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(4)}
              agentStep={3}
              agentOutputKey="content_output"
              summaryStats={summaryStats}
            />
          )}
        </div>
      )
    }
  }

  // Step 4: Sales Agent
  if (stepIndex === 4) {
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={5} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Generating sales outreach...</p>
          </div>
          <div className="rounded-2xl border border-ink/10 bg-white p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Progress</p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    if (output) {
      const salesOutput = output as SalesOutput
      const seqCount = salesOutput.email_sequences?.length ?? 0
      const linkedInCount = salesOutput.linkedin_templates?.length ?? 0
      const summaryStats = `${seqCount} email sequence${seqCount !== 1 ? 's' : ''}, ${linkedInCount} LinkedIn template${linkedInCount !== 1 ? 's' : ''}`

      // Build segments from audience output (step 2)
      const audienceOutput = agentOutputs[2] as AudienceOutput | undefined
      const voiceSegments = (audienceOutput?.segments ?? []).map((seg) => ({
        name: seg.name,
        description: seg.reasoning ?? `${seg.fit_label ?? ''} fit segment`.trim(),
      }))

      // Build salesScripts: concatenate email bodies per segment
      const salesScripts: Record<string, string> = {}
      for (const seq of salesOutput.email_sequences ?? []) {
        const bodies = (seq.emails ?? []).map((e) => `Subject: ${e.subject}\n\n${e.body}`).join('\n\n---\n\n')
        salesScripts[seq.segment] = bodies
      }

      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={5} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Sales Outreach ready</p>
          </div>

          <SalesView output={salesOutput} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(5)}
              agentStep={4}
              agentOutputKey="sales_output"
              summaryStats={summaryStats}
            />
          )}

          {runId && (
            <div className="mt-8 border-t border-ink/10 pt-8">
              <div className="flex flex-col gap-2 mb-6">
                <h3 className="font-display text-lg font-bold text-ink">Launch Voice Sales Agent</h3>
                <p className="text-sm text-ink-muted">
                  Pick a segment, review the script, and place a live outbound call — powered by ElevenLabs Conversational AI.
                </p>
              </div>
              <VoiceAgentPanel
                runId={runId}
                segments={voiceSegments}
                salesScripts={salesScripts}
              />
            </div>
          )}
        </div>
      )
    }
  }

  // Step 5: Ads Agent
  if (stepIndex === 5) {
    if (isRunning && !output) {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={6} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Generating ad creative...</p>
          </div>
          <div className="rounded-2xl border border-ink/10 bg-white p-6">
            <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Progress</p>
            <ProgressTimeline steps={researchProgress} />
          </div>
        </div>
      )
    }

    if (output) {
      const adsOutput = output as AdsOutput
      const adCopyCount = adsOutput.ad_copies?.length ?? 0
      const abCount = adsOutput.ab_variations?.length ?? 0
      const imageCount = adsOutput.ad_visuals?.filter((v) => v.image_url).length ?? 0
      const summaryStats = `${adCopyCount} ad cop${adCopyCount !== 1 ? 'ies' : 'y'}, ${abCount} A/B variation${abCount !== 1 ? 's' : ''}, ${imageCount} image${imageCount !== 1 ? 's' : ''} generated`

      return (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <StepBadge number={6} />
              <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
            </div>
            <p className="text-ink-muted text-sm ml-11">Ad Creative ready</p>
          </div>

          <AdsView output={adsOutput} />

          {runId && (
            <ApprovalGate
              output={output}
              runId={runId}
              onDecisionComplete={() => setStep(6)}
              agentStep={5}
              agentOutputKey="ads_output"
              summaryStats={summaryStats}
            />
          )}
        </div>
      )
    }
  }

  // Pipeline complete (step >= 6) or unrecognized step
  if (stepIndex >= 6) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-full bg-success/10 border border-success/30 flex items-center justify-center text-success text-sm font-bold">
              ✓
            </span>
            <h2 className="font-display text-2xl font-bold text-ink">Pipeline Complete</h2>
          </div>
          <p className="text-ink-muted text-sm ml-11">All 6 agents have completed and been approved.</p>
        </div>
        <div className="rounded-2xl border border-success/15 bg-success/5 p-6 flex flex-col items-center gap-3">
          <p className="text-success font-semibold text-sm">Your full marketing pipeline is ready.</p>
          <p className="text-ink-faint text-xs text-center">Research, Profile, Audience, Content, Sales, and Ads — all approved and ready to deploy.</p>
        </div>
      </div>
    )
  }

  // Fallback: step without output yet (waiting for pipeline)
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <StepBadge number={stepIndex + 1} />
          <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
        </div>
        <p className="text-ink-muted text-sm ml-11">Waiting for pipeline...</p>
      </div>
      <div className="rounded-2xl border border-ink/10 bg-white p-6 min-h-[200px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-ink-faint">
          <div className="w-10 h-10 rounded-full border-2 border-ink/20 border-dashed flex items-center justify-center">
            <span className="text-lg">...</span>
          </div>
          <p className="text-sm">Agent output will appear here</p>
        </div>
      </div>
    </div>
  )
}
