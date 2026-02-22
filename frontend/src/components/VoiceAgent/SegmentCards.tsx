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
      <p className="text-sm text-zinc-400 font-medium">Select an audience segment for the voice call</p>
      {segments.length === 0 && (
        <p className="text-sm text-zinc-600 italic">No segments available. Complete the Audience step first.</p>
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
                  ? 'border-blue-500/60 bg-blue-500/10 ring-2 ring-blue-500/30'
                  : 'border-white/10 bg-white/3 hover:border-white/20 hover:bg-white/5'
              }`}
            >
              <p className={`text-sm font-semibold ${isSelected ? 'text-blue-300' : 'text-white'}`}>
                {segment.name}
              </p>
              <p className="text-xs text-zinc-400 leading-relaxed line-clamp-3">{segment.description}</p>
              {isSelected && (
                <span className="inline-flex items-center gap-1 text-xs text-blue-400 font-medium mt-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
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
