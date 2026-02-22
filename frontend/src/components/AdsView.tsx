import { useState } from 'react'
import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'
import { useBlitzStore } from '../store/useBlitzStore'

// TypeScript interfaces matching backend Pydantic schemas
export interface AdCopy {
  segment: string
  platform: string
  headline: string
  body: string
  cta: string
}

export interface AdVisual {
  segment: string
  platform: string
  visual_concept: string
  color_palette: string[]
  image_prompt: string
  image_url: string | null
}

export interface AbVariation {
  ad_copy_ref: string
  variant_label: string
  headline: string
  body: string
  cta: string
  test_hypothesis: string
  image_prompt: string
  image_url: string | null
}

export interface AdsOutput {
  ad_copies: AdCopy[]
  ad_visuals: AdVisual[]
  ab_variations: AbVariation[]
}

interface AdsViewProps {
  output: AdsOutput
}

const PLATFORM_BADGE: Record<string, string> = {
  'Google Ads': 'bg-blue-500/10 border-blue-500/20 text-blue-300',
  'Meta Ads': 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300',
  'LinkedIn Ads': 'bg-sky-500/10 border-sky-500/20 text-sky-300',
  Google: 'bg-blue-500/10 border-blue-500/20 text-blue-300',
  Meta: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300',
  LinkedIn: 'bg-sky-500/10 border-sky-500/20 text-sky-300',
}

const IMAGE_CAP = 3

function ImageGenerator({
  initialPrompt,
  imageUrl,
  label,
  imagesGenerated,
  onImageGenerated,
}: {
  initialPrompt: string
  imageUrl: string | null
  label?: string
  imagesGenerated: number
  onImageGenerated: (url: string) => void
}) {
  const runId = useBlitzStore((s) => s.runId)
  const [prompt, setPrompt] = useState(initialPrompt)
  const [localUrl, setLocalUrl] = useState(imageUrl)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const displayUrl = localUrl ?? imageUrl
  const limitReached = imagesGenerated >= IMAGE_CAP && !displayUrl

  async function handleGenerate() {
    if (!runId || !prompt.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`http://localhost:8000/ads/${runId}/generate-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
      const data = await res.json()
      if (data.image_url) {
        setLocalUrl(data.image_url)
        onImageGenerated(data.image_url)
      } else if (data.error) {
        setError(data.error)
      } else {
        setError('Image generation failed. Try editing the prompt.')
      }
    } catch {
      setError('Network error. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  if (displayUrl) {
    return (
      <img
        src={displayUrl}
        alt={label ?? 'Ad visual'}
        className="rounded-xl border border-white/8 w-full max-h-64 object-cover"
      />
    )
  }

  return (
    <div className="rounded-xl border border-dashed border-white/10 bg-white/2 p-4 flex flex-col gap-3">
      <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium">Image Prompt</p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
        className="w-full rounded-lg bg-zinc-800/50 border border-white/10 px-3 py-2 text-xs text-zinc-300 leading-relaxed resize-none focus:outline-none focus:border-violet-500/50 transition-colors"
        placeholder="Describe the image you want..."
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <button
        onClick={handleGenerate}
        disabled={loading || limitReached || !prompt.trim()}
        className={`self-start rounded-lg px-4 py-2 text-xs font-semibold border transition-all ${
          loading
            ? 'bg-violet-600/10 border-violet-500/20 text-violet-400 animate-pulse cursor-wait'
            : limitReached
              ? 'bg-zinc-800/50 border-white/8 text-zinc-600 cursor-not-allowed'
              : 'bg-violet-600/15 border-violet-500/30 text-violet-300 hover:bg-violet-600/25 hover:border-violet-500/50'
        }`}
      >
        {loading ? 'Generating...' : limitReached ? `Limit reached (${IMAGE_CAP})` : 'Generate Image'}
      </button>
      {!limitReached && !loading && (
        <p className="text-xs text-zinc-600">{IMAGE_CAP - imagesGenerated} of {IMAGE_CAP} generations remaining</p>
      )}
    </div>
  )
}

export default function AdsView({ output }: AdsViewProps) {
  const { ad_copies = [], ad_visuals = [], ab_variations = [] } = output
  const [activeVariations, setActiveVariations] = useState<Record<number, number>>({})
  const [imagesGenerated, setImagesGenerated] = useState(0)

  function handleImageGenerated(_url: string) {
    setImagesGenerated((prev) => prev + 1)
  }

  // Group A/B variations by ad_copy_ref for toggle display
  const groupedVariations: Record<string, AbVariation[]> = {}
  for (const v of ab_variations) {
    const key = v.ad_copy_ref ?? 'ungrouped'
    if (!groupedVariations[key]) groupedVariations[key] = []
    groupedVariations[key].push(v)
  }

  return (
    <div className="rounded-2xl border border-white/8 bg-white/3 overflow-hidden">
      <TabGroup>
        <TabList className="flex border-b border-white/8 overflow-x-auto">
          {['Ad Copy', 'Visuals', 'A/B Variations'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 min-w-max px-4 py-3 text-sm font-medium text-zinc-500 hover:text-zinc-300 data-[selected]:text-white data-[selected]:bg-white/5 data-[selected]:border-b-2 data-[selected]:border-violet-500 transition-colors outline-none"
            >
              {tab}
            </Tab>
          ))}
        </TabList>

        <TabPanels>
          {/* Ad Copy Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {ad_copies.length === 0 && (
              <p className="text-sm text-zinc-600 italic">No ad copy generated.</p>
            )}
            {ad_copies.map((ad, i) => {
              const badgeClass = PLATFORM_BADGE[ad.platform] ?? 'bg-violet-500/10 border-violet-500/20 text-violet-300'
              return (
                <div key={i} className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badgeClass}`}>
                      {ad.platform}
                    </span>
                    <span className="text-xs text-zinc-500">{ad.segment}</span>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Headline</p>
                    <p className="text-sm font-bold text-white">{ad.headline}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Body</p>
                    <p className="text-xs text-zinc-300 leading-relaxed">{ad.body}</p>
                  </div>
                  {ad.cta && (
                    <div className="self-start rounded-xl bg-emerald-600/10 border border-emerald-500/20 px-4 py-2">
                      <p className="text-xs text-emerald-400 font-semibold">{ad.cta}</p>
                    </div>
                  )}
                </div>
              )
            })}
          </TabPanel>

          {/* Visuals Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {ad_visuals.length === 0 && (
              <p className="text-sm text-zinc-600 italic">No ad visuals generated.</p>
            )}
            {ad_visuals.map((visual, i) => (
              <div key={i} className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${PLATFORM_BADGE[visual.platform] ?? 'bg-violet-500/10 border-violet-500/20 text-violet-300'}`}>
                    {visual.platform}
                  </span>
                  <span className="text-xs text-zinc-500">{visual.segment}</span>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Visual Concept</p>
                  <p className="text-xs text-zinc-300 leading-relaxed">{visual.visual_concept}</p>
                </div>
                {visual.color_palette && visual.color_palette.length > 0 && (
                  <div className="flex items-center gap-2">
                    <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium">Palette</p>
                    <div className="flex gap-1">
                      {visual.color_palette.map((color, ci) => (
                        <div
                          key={ci}
                          className="w-5 h-5 rounded-full border border-white/10"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                  </div>
                )}
                <ImageGenerator
                  initialPrompt={visual.image_prompt ?? ''}
                  imageUrl={visual.image_url}
                  label={`${visual.segment} - ${visual.platform}`}
                  imagesGenerated={imagesGenerated}
                  onImageGenerated={handleImageGenerated}
                />
              </div>
            ))}
          </TabPanel>

          {/* A/B Variations Tab */}
          <TabPanel className="p-6 flex flex-col gap-6">
            {ab_variations.length === 0 && (
              <p className="text-sm text-zinc-600 italic">No A/B variations generated.</p>
            )}
            {Object.entries(groupedVariations).map(([ref, variations], groupIdx) => (
              <div key={groupIdx} className="flex flex-col gap-3">
                <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium">{ref}</p>
                <div className="flex gap-2">
                  {variations.map((_, vi) => (
                    <button
                      key={vi}
                      onClick={() => setActiveVariations((prev) => ({ ...prev, [groupIdx]: vi }))}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition-all ${
                        (activeVariations[groupIdx] ?? 0) === vi
                          ? 'bg-violet-600/20 border-violet-500/40 text-violet-300'
                          : 'bg-white/3 border-white/8 text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      Variant {variations[vi].variant_label}
                    </button>
                  ))}
                </div>
                {(() => {
                  const active = variations[activeVariations[groupIdx] ?? 0]
                  if (!active) return null
                  return (
                    <div className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3">
                      {active.test_hypothesis && (
                        <div className="rounded-xl border border-amber-500/15 bg-amber-500/5 px-4 py-2">
                          <p className="text-xs text-amber-400 uppercase tracking-widest font-medium mb-0.5">Hypothesis</p>
                          <p className="text-xs text-zinc-300">{active.test_hypothesis}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Headline</p>
                        <p className="text-sm font-bold text-white">{active.headline}</p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Body</p>
                        <p className="text-xs text-zinc-300 leading-relaxed">{active.body}</p>
                      </div>
                      {active.cta && (
                        <div className="self-start rounded-xl bg-emerald-600/10 border border-emerald-500/20 px-4 py-2">
                          <p className="text-xs text-emerald-400 font-semibold">{active.cta}</p>
                        </div>
                      )}
                      <ImageGenerator
                        initialPrompt={active.image_prompt ?? ''}
                        imageUrl={active.image_url}
                        label={`Variant ${active.variant_label}`}
                        imagesGenerated={imagesGenerated}
                        onImageGenerated={handleImageGenerated}
                      />
                    </div>
                  )
                })()}
              </div>
            ))}
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  )
}
