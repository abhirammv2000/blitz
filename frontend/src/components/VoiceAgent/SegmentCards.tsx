interface Segment {
  name: string
  description: string
}

interface SegmentCardsProps {
  segments: Segment[]
  onSelect: (segment: Segment) => void
  selectedSegment?: Segment | null
}

export default function SegmentCards({ segments, onSelect, selectedSegment }: SegmentCardsProps) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-ink-muted font-medium">Select an audience segment for the voice call</p>
      {segments.length === 0 && (
        <p className="text-sm text-ink-faint italic">No segments available. Complete the Audience step first.</p>
      )}
      <div className="flex flex-row gap-3 overflow-x-auto pb-2">
        {segments.map((segment, i) => {
          const isSelected = selectedSegment?.name === segment.name
          return (
            <button
              key={i}
              onClick={() => onSelect(segment)}
              className={`flex-shrink-0 w-56 rounded-xl border p-4 text-left transition-all cursor-pointer flex flex-col gap-2 ${
                isSelected
                  ? 'border-teal-600/60 bg-teal-100 ring-2 ring-teal-600/20'
                  : 'border-ink/10 bg-white hover:border-ink/20 hover:bg-cream'
              }`}
            >
              <p className={`text-sm font-semibold ${isSelected ? 'text-teal-700' : 'text-ink'}`}>
                {segment.name}
              </p>
              <p className="text-xs text-ink-muted leading-relaxed line-clamp-3">{segment.description}</p>
              {isSelected && (
                <span className="inline-flex items-center gap-1 text-xs text-teal-600 font-medium mt-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-600 flex-shrink-0" />
                  Selected
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
