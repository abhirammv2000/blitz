import { useBlitzStore } from '../store/useBlitzStore'
import { InstagramCard } from './InstagramCard'
import { EmailPreview } from './EmailPreview'
import { AdMockup } from './AdMockup'
import type { ContentOutput } from './ContentView'
import type { AdsOutput } from './AdsView'

function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="flex flex-col gap-1 mb-6">
      <h2 className="font-display text-xl font-bold text-ink">{title}</h2>
      {subtitle && <p className="font-body text-sm text-ink-muted">{subtitle}</p>}
    </div>
  )
}

function Placeholder({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-ink/8 bg-cream-dark p-8 flex items-center justify-center">
      <p className="font-body text-sm text-ink-faint italic">{label}</p>
    </div>
  )
}

export default function SummaryPage() {
  const { agentOutputs } = useBlitzStore()

  const contentOutput = agentOutputs[3] as ContentOutput | undefined
  const adsOutput = agentOutputs[5] as AdsOutput | undefined

  // Pick first social post (prefer Instagram, fall back to first)
  const socialPosts = contentOutput?.social_posts ?? []
  const instagramPost =
    socialPosts.find((p) => p.platform.toLowerCase().includes('instagram')) ?? socialPosts[0]

  // Pick first email campaign
  const emailCampaign = contentOutput?.email_campaigns?.[0]

  // Pick first two A/B variations
  const abVariations = adsOutput?.ab_variations ?? []
  const varA = abVariations[0]
  const varB = abVariations[1]

  // Infer brand name from store (from first output key that has a company reference, or use generic)
  const profileOutput = agentOutputs[1] as { company_name?: string; brand_name?: string } | undefined
  const brandName = profileOutput?.company_name ?? profileOutput?.brand_name ?? 'Brand'

  return (
    <div className="flex flex-col gap-12">
      {/* Page header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-full bg-teal-100 border border-teal-600/30 flex items-center justify-center text-teal-700 text-sm font-bold flex-shrink-0">
            7
          </span>
          <h1 className="font-display text-3xl font-black text-ink">Your Marketing Package</h1>
        </div>
        <p className="font-body text-ink-muted text-sm ml-11">
          All pipeline outputs rendered as platform-native artifacts — ready to deploy.
        </p>
      </div>

      {/* Social Media section */}
      <section>
        <SectionHeading
          title="Social Media"
          subtitle="Instagram post preview — generated from your content strategy"
        />
        {instagramPost ? (
          <InstagramCard post={instagramPost} brandName={brandName} />
        ) : (
          <Placeholder label="Social posts not yet available — complete the Content Strategist step to see previews" />
        )}
      </section>

      {/* Email Campaign section */}
      <section>
        <SectionHeading
          title="Email Campaign"
          subtitle="First email campaign from your content strategy"
        />
        {emailCampaign ? (
          <EmailPreview email={emailCampaign} />
        ) : (
          <Placeholder label="Email campaigns not yet available — complete the Content Strategist step to see previews" />
        )}
      </section>

      {/* Ad Creatives section */}
      <section>
        <SectionHeading
          title="Ad Creatives"
          subtitle="A/B variations from your ad creative agent"
        />
        {varA && varB ? (
          <AdMockup varA={varA} varB={varB} />
        ) : varA ? (
          <AdMockup varA={varA} varB={{ variant_label: 'Pending', headline: 'Variation B', body: 'A second variation was not generated.', cta: 'Learn More', test_hypothesis: '', image_url: null }} />
        ) : (
          <Placeholder label="Ad creatives not yet available — complete the Ad Creative step to see previews" />
        )}
      </section>
    </div>
  )
}
