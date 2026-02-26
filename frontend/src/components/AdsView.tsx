import { useState } from 'react'
import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'
import { useBlitzStore } from '../store/useBlitzStore'
import { API_BASE } from '../config'

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
  'Google Ads': 'bg-blue-500/10 border-blue-500/20 text-blue-700',
  'Meta Ads': 'bg-indigo-500/10 border-indigo-500/20 text-indigo-700',
  'LinkedIn Ads': 'bg-sky-500/10 border-sky-500/20 text-sky-700',
  Google: 'bg-blue-500/10 border-blue-500/20 text-blue-700',
  Meta: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-700',
  LinkedIn: 'bg-sky-500/10 border-sky-500/20 text-sky-700',
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
      const res = await fetch(`${API_BASE}/ads/${runId}/generate-image`, {
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
        className="rounded-xl border border-ink/10 w-full max-h-64 object-cover"
      />
    )
  }

  return (
    <div className="rounded-xl border border-dashed border-ink/15 bg-cream p-4 flex flex-col gap-3">
      <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">Image Prompt</p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
        className="w-full rounded-lg bg-white border border-ink/10 px-3 py-2 text-xs text-ink leading-relaxed resize-none focus:outline-none focus:border-teal-600/40 transition-colors"
        placeholder="Describe the image you want..."
      />
      {error && <p className="text-xs text-error">{error}</p>}
      <button
        onClick={handleGenerate}
        disabled={loading || limitReached || !prompt.trim()}
        className={`self-start rounded-lg px-4 py-2 text-xs font-semibold border transition-all ${
          loading
            ? 'bg-teal-100 border-teal-600/20 text-teal-600 animate-pulse cursor-wait'
            : limitReached
              ? 'bg-cream-dark border-ink/10 text-ink-faint cursor-not-allowed'
              : 'bg-teal-100 border-teal-600/20 text-teal-700 hover:bg-teal-100/80 hover:border-teal-600/40'
        }`}
      >
        {loading ? 'Generating...' : limitReached ? `Limit reached (${IMAGE_CAP})` : 'Generate Image'}
      </button>
      {!limitReached && !loading && (
        <p className="text-xs text-ink-faint">{IMAGE_CAP - imagesGenerated} of {IMAGE_CAP} generations remaining</p>
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
    <div className="rounded-2xl border border-ink/10 bg-white overflow-hidden">
      <TabGroup>
        <TabList className="flex border-b border-ink/10 overflow-x-auto">
          {['Ad Copy', 'Visuals', 'A/B Variations'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 min-w-max px-4 py-3 text-sm font-medium text-ink-muted hover:text-ink data-[selected]:text-ink data-[selected]:bg-cream-dark data-[selected]:border-b-2 data-[selected]:border-teal-600 transition-colors outline-none"
            >
              {tab}
            </Tab>
          ))}
        </TabList>

        <TabPanels>
          {/* Ad Copy Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {ad_copies.length === 0 && (
              <p className="text-sm text-ink-faint italic">No ad copy generated.</p>
            )}
            {ad_copies.map((ad, i) => {
              const badgeClass = PLATFORM_BADGE[ad.platform] ?? 'bg-teal-100 border-teal-600/20 text-teal-700'
              return (
                <div key={i} className="rounded-xl border border-ink/10 bg-cream p-4 flex flex-col gap-3">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badgeClass}`}>
                      {ad.platform}
                    </span>
                    <span className="text-xs text-ink-faint">{ad.segment}</span>
                  </div>
                  <div>
                    <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Headline</p>
                    <p className="text-sm font-bold text-ink">{ad.headline}</p>
                  </div>
                  <div>
                    <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Body</p>
                    <p className="text-xs text-ink-muted leading-relaxed">{ad.body}</p>
                  </div>
                  {ad.cta && (
                    <div className="self-start rounded-xl bg-teal-600 px-4 py-2">
                      <p className="text-xs text-white font-semibold">{ad.cta}</p>
                    </div>
                  )}
                </div>
              )
            })}
          </TabPanel>

          {/* Visuals Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {ad_visuals.length === 0 && (
              <p className="text-sm text-ink-faint italic">No ad visuals generated.</p>
            )}
            {ad_visuals.map((visual, i) => (
              <div key={i} className="rounded-xl border border-ink/10 bg-cream p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${PLATFORM_BADGE[visual.platform] ?? 'bg-teal-100 border-teal-600/20 text-teal-700'}`}>
                    {visual.platform}
                  </span>
                  <span className="text-xs text-ink-faint">{visual.segment}</span>
                </div>
                <div>
                  <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Visual Concept</p>
                  <p className="text-xs text-ink-muted leading-relaxed">{visual.visual_concept}</p>
                </div>
                {visual.color_palette && visual.color_palette.length > 0 && (
                  <div className="flex items-center gap-2">
                    <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">Palette</p>
                    <div className="flex gap-1">
                      {visual.color_palette.map((color, ci) => (
                        <div
                          key={ci}
                          className="w-5 h-5 rounded-full border border-ink/10"
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
              <p className="text-sm text-ink-faint italic">No A/B variations generated.</p>
            )}
            {Object.entries(groupedVariations).map(([ref, variations], groupIdx) => (
              <div key={groupIdx} className="flex flex-col gap-3">
                <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">{ref}</p>
                <div className="flex gap-2">
                  {variations.map((_, vi) => (
                    <button
                      key={vi}
                      onClick={() => setActiveVariations((prev) => ({ ...prev, [groupIdx]: vi }))}
                      className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition-all ${
                        (activeVariations[groupIdx] ?? 0) === vi
                          ? 'bg-teal-100 border-teal-600/40 text-teal-700'
                          : 'bg-cream-dark border-ink/10 text-ink-muted hover:text-ink'
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
                    <div className="rounded-xl border border-ink/10 bg-cream p-4 flex flex-col gap-3">
                      {active.test_hypothesis && (
                        <div className="rounded-xl border border-gold-400/15 bg-gold-100/50 px-4 py-2">
                          <p className="text-xs text-gold-600 uppercase tracking-widest font-medium mb-0.5">Hypothesis</p>
                          <p className="text-xs text-ink">{active.test_hypothesis}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Headline</p>
                        <p className="text-sm font-bold text-ink">{active.headline}</p>
                      </div>
                      <div>
                        <p className="text-xs text-ink-faint uppercase tracking-widest font-medium mb-1">Body</p>
                        <p className="text-xs text-ink-muted leading-relaxed">{active.body}</p>
                      </div>
                      {active.cta && (
                        <div className="self-start rounded-xl bg-teal-600 px-4 py-2">
                          <p className="text-xs text-white font-semibold">{active.cta}</p>
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
