interface AdVariation {
  ad_copy_ref?: string
  variant_label: string
  headline: string
  body: string
  cta: string
  test_hypothesis: string
  image_prompt?: string
  image_url: string | null
}

interface AdMockupProps {
  varA: AdVariation
  varB: AdVariation
}

export function AdMockup({ varA, varB }: AdMockupProps) {
  return (
    <div className="flex gap-4">
      {[varA, varB].map((v, i) => (
        <div key={i} className="flex-1 rounded-2xl border border-ink/10 bg-white shadow-md p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="font-body text-xs font-semibold uppercase tracking-widest text-ink-muted">
              Variation {i === 0 ? 'A' : 'B'}
            </span>
            <span className="font-body text-xs text-ink-faint">{v.variant_label}</span>
          </div>
          {/* Image placeholder */}
          <div className="w-full aspect-video rounded-xl bg-gradient-to-br from-teal-100 to-gold-100 mb-4 flex items-center justify-center overflow-hidden">
            {v.image_url ? (
              <img src={v.image_url} className="w-full h-full object-cover" alt="" />
            ) : (
              <span className="font-body text-xs text-ink-faint">Image</span>
            )}
          </div>
          <p className="font-display text-base font-bold text-ink mb-1">{v.headline}</p>
          <p className="font-body text-sm text-ink-muted mb-3">{v.body}</p>
          <button className="w-full py-2 rounded-lg bg-teal-600 text-white font-body text-sm font-semibold hover:bg-teal-700 transition-colors">
            {v.cta}
          </button>
          <p className="font-body text-xs text-ink-faint mt-2 italic">{v.test_hypothesis}</p>
        </div>
      ))}
    </div>
  )
}

export default AdMockup
