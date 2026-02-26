import { type ReactNode } from 'react'
import { useBlitzStore } from '../store/useBlitzStore'
import DossierView from './DossierView'
import ProfileView from './ProfileView'
import AudienceView from './AudienceView'
import ContentView from './ContentView'
import SalesView from './SalesView'
import AdsView from './AdsView'
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
  readOnly?: boolean
}

function StepBadge({ number }: { number: number | string }) {
  return (
    <span className="w-8 h-8 rounded-full bg-teal-100 border border-teal-600/30 flex items-center justify-center text-teal-700 text-sm font-bold flex-shrink-0">
      {number}
    </span>
  )
}

function StepHeader({ displayNumber, agentName, subtitle }: { displayNumber: number; agentName: string; subtitle: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <StepBadge number={displayNumber} />
        <h2 className="font-display text-2xl font-bold text-ink">{agentName}</h2>
      </div>
      <p className="text-ink-muted text-sm ml-11">{subtitle}</p>
    </div>
  )
}

function LoadingState({ displayNumber, agentName, subtitle, progress }: { displayNumber: number; agentName: string; subtitle: string; progress: unknown[] }) {
  return (
    <div className="flex flex-col gap-6">
      <StepHeader displayNumber={displayNumber} agentName={agentName} subtitle={subtitle} />
      <div className="rounded-2xl border border-ink/10 bg-white p-6">
        <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-4">Progress</p>
        <ProgressTimeline steps={progress} />
      </div>
    </div>
  )
}

function WaitingState({ displayNumber, agentName, message }: { displayNumber: number; agentName: string; message: string }) {
  return (
    <div className="flex flex-col gap-6">
      <StepHeader displayNumber={displayNumber} agentName={agentName} subtitle="Waiting for pipeline..." />
      <div className="rounded-2xl border border-ink/10 bg-white p-6 min-h-[200px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-ink-faint">
          <div className="w-10 h-10 rounded-full border-2 border-ink/20 border-dashed flex items-center justify-center">
            <span className="text-lg">...</span>
          </div>
          <p className="text-sm">{message}</p>
        </div>
      </div>
    </div>
  )
}

interface StepLayoutProps {
  displayNumber: number
  agentName: string
  subtitle: string
  children: ReactNode
}

function StepLayout({ displayNumber, agentName, subtitle, children }: StepLayoutProps) {
  return (
    <div className="flex flex-col gap-6">
      <StepHeader displayNumber={displayNumber} agentName={agentName} subtitle={subtitle} />
      {children}
    </div>
  )
}

export default function AgentStep({ stepIndex, agentName }: AgentStepProps) {
  const { agentOutputs, researchProgress, isRunning, runId } = useBlitzStore()
  const output = agentOutputs[stepIndex]
  const displayNumber = stepIndex + 1

  // Loading state (running, no output yet)
  if (isRunning && !output) {
    const loadingMessages: Record<number, string> = {
      0: 'Researching your company...',
      1: 'Synthesizing marketing profile...',
      2: 'Generating audience segments...',
      3: 'Generating content strategy...',
      4: 'Generating sales outreach...',
      5: 'Generating ad creative...',
    }
    return (
      <LoadingState
        displayNumber={displayNumber}
        agentName={agentName}
        subtitle={loadingMessages[stepIndex] ?? 'Processing...'}
        progress={researchProgress}
      />
    )
  }

  // No output and not running: waiting state
  if (!output) {
    const waitingMessages: Record<number, string> = {
      0: 'Research will begin shortly',
    }
    return (
      <WaitingState
        displayNumber={displayNumber}
        agentName={agentName}
        message={waitingMessages[stepIndex] ?? 'Agent output will appear here'}
      />
    )
  }

  // Step 0: Research Scout
  if (stepIndex === 0) {
    return (
      <StepLayout displayNumber={1} agentName={agentName} subtitle="Company Intelligence Dossier ready">
        <DossierView output={output as ResearchOutput} />
      </StepLayout>
    )
  }

  // Step 1: Marketing Profile
  if (stepIndex === 1) {
    return (
      <StepLayout displayNumber={2} agentName={agentName} subtitle="Marketing Profile ready">
        <ProfileView profile={output as MarketingProfile} />
      </StepLayout>
    )
  }

  // Step 2: Audience Segments
  if (stepIndex === 2) {
    return (
      <StepLayout displayNumber={3} agentName={agentName} subtitle="Audience Segments ready">
        <AudienceView output={output as AudienceOutput} runId={runId ?? ''} />
      </StepLayout>
    )
  }

  // Step 3: Content Strategist
  if (stepIndex === 3) {
    return (
      <StepLayout displayNumber={4} agentName={agentName} subtitle="Content Strategy ready">
        <ContentView output={output as ContentOutput} />
      </StepLayout>
    )
  }

  // Step 4: Sales Agent
  if (stepIndex === 4) {
    const salesOutput = output as SalesOutput
    const audienceOutput = agentOutputs[2] as AudienceOutput | undefined
    const voiceSegments = (audienceOutput?.segments ?? []).map((seg) => ({
      name: seg.name,
      description: seg.reasoning ?? `${seg.fit_label ?? ''} fit segment`.trim(),
    }))

    const salesScripts: Record<string, string> = {}
    for (const seq of salesOutput.email_sequences ?? []) {
      const bodies = (seq.emails ?? []).map((e) => `Subject: ${e.subject}\n\n${e.body}`).join('\n\n---\n\n')
      salesScripts[seq.segment] = bodies
    }

    const researchOutput = agentOutputs[0] as ResearchOutput | undefined
    const companyName = researchOutput?.company_name ?? ''

    return (
      <StepLayout displayNumber={5} agentName={agentName} subtitle="Sales Outreach ready">
        <SalesView output={salesOutput} />
        {runId && (
          <div className="mt-8 border-t border-ink/10 pt-8">
            <div className="flex flex-col gap-2 mb-6">
              <h3 className="font-display text-lg font-bold text-ink">Launch Voice Sales Agent</h3>
              <p className="text-sm text-ink-muted">
                Pick a segment, review the script, and place a live outbound call — powered by ElevenLabs Conversational AI.
              </p>
            </div>
            <VoiceAgentPanel runId={runId} segments={voiceSegments} salesScripts={salesScripts} companyName={companyName} />
          </div>
        )}
      </StepLayout>
    )
  }

  // Step 5: Ads Agent
  if (stepIndex === 5) {
    return (
      <StepLayout displayNumber={6} agentName={agentName} subtitle="Ad Creative ready">
        <AdsView output={output as AdsOutput} />
      </StepLayout>
    )
  }

  return (
    <WaitingState
      displayNumber={displayNumber}
      agentName={agentName}
      message="Agent output will appear here"
    />
  )
}
