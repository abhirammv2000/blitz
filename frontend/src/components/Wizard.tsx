import { useBlitzStore } from '../store/useBlitzStore'
import AgentStep from './AgentStep'

const AGENTS = [
  { name: 'Research Scout', description: 'Company intelligence & competitor analysis' },
  { name: 'Marketing Profile', description: 'Brand DNA, positioning & USPs' },
  { name: 'Audience Identifier', description: 'Synthetic audience segments' },
  { name: 'Content Strategist', description: 'Social, email, blog & calendar' },
  { name: 'Sales Agent', description: 'Outreach sequences & pipeline stages' },
  { name: 'Ad Creative', description: 'Ad copy, visuals & A/B variants' },
  { name: 'Marketing Package', description: 'Your complete marketing materials' },
]

function StepStatus({ index, currentStep }: { index: number; currentStep: number }) {
  if (index < currentStep) {
    // Completed
    return (
      <div className="w-6 h-6 rounded-full bg-success flex items-center justify-center flex-shrink-0">
        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    )
  }
  if (index === currentStep) {
    // Active
    return (
      <div className="w-6 h-6 rounded-full border-2 border-teal-600 bg-teal-100 flex items-center justify-center flex-shrink-0">
        <div className="w-2 h-2 rounded-full bg-teal-600 animate-pulse" />
      </div>
    )
  }
  // Pending
  return (
    <div className="w-6 h-6 rounded-full border-2 border-ink/20 bg-cream-dark flex items-center justify-center flex-shrink-0">
      <span className="text-ink-faint text-xs font-medium">{index + 1}</span>
    </div>
  )
}

export default function Wizard() {
  const { currentStep, runId } = useBlitzStore()

  return (
    <div className="min-h-screen bg-cream flex">
      {/* Sidebar — step indicator */}
      <aside className="w-72 border-r border-ink/10 bg-cream-dark flex flex-col py-8 px-6 gap-2">
        {/* Blitz wordmark */}
        <div className="mb-8">
          <h1 className="font-display text-2xl font-black tracking-tighter bg-gradient-to-r from-teal-700 to-gold-500 bg-clip-text text-transparent">
            Blitz
          </h1>
          {runId && (
            <p className="text-ink-faint text-xs mt-1 truncate">
              Run: {runId.slice(0, 8)}...
            </p>
          )}
        </div>

        {/* Steps */}
        <div className="flex flex-col gap-1">
          {AGENTS.map((agent, index) => {
            const isActive = index === currentStep
            const isComplete = index < currentStep

            return (
              <div
                key={index}
                className={`flex items-start gap-3 p-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-teal-100 border border-teal-600/20'
                    : 'border border-transparent hover:bg-white/60'
                }`}
              >
                <div className="mt-0.5">
                  <StepStatus index={index} currentStep={currentStep} />
                </div>
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span
                    className={`text-sm font-semibold truncate ${
                      isActive ? 'text-teal-700' : isComplete ? 'text-ink-muted' : 'text-ink-faint'
                    }`}
                  >
                    {agent.name}
                  </span>
                  <span className="text-xs text-ink-faint truncate">
                    {agent.description}
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Connector line — visual guide between steps */}
        <div className="mt-auto pt-6 border-t border-ink/10">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-teal-600" />
            <p className="text-ink-faint text-xs">
              Step {currentStep + 1} of {AGENTS.length}
            </p>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto bg-cream">
        <div className="max-w-3xl mx-auto py-12 px-8">
          <AgentStep
            stepIndex={currentStep}
            agentName={AGENTS[currentStep]?.name ?? 'Agent'}
          />
        </div>
      </main>
    </div>
  )
}
