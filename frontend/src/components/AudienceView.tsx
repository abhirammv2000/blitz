import SegmentCard from './SegmentCard'
import type { AudienceSegment } from './SegmentCard'

// TypeScript interface matching backend Pydantic AudienceOutput schema
export interface AudienceOutput {
  segments: AudienceSegment[]
}

interface AudienceViewProps {
  output: AudienceOutput
  runId: string
}

export default function AudienceView({ output }: AudienceViewProps) {
  const segments = output.segments ?? []
  const highFitCount = segments.filter((s) => s.fit_label === 'High').length

  return (
    <div className="flex flex-col gap-3">
      {/* Summary stats */}
      <p className="text-xs text-zinc-500">
        {segments.length} segment{segments.length !== 1 ? 's' : ''} generated
        {highFitCount > 0 && (
          <> &mdash; <span className="text-green-400 font-medium">{highFitCount} high-fit</span></>
        )}
      </p>

      {/* Horizontal scrollable cards */}
      <div className="flex flex-row gap-4 overflow-x-auto pb-4">
        {segments.map((segment, i) => (
          <SegmentCard key={i} segment={segment} index={i} />
        ))}
        {segments.length === 0 && (
          <p className="text-sm text-zinc-600 italic">No segments generated.</p>
        )}
      </div>
    </div>
  )
}
