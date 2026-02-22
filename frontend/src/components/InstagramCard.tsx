interface InstagramCardProps {
  post: { platform: string; post_copy: string; hashtags: string[]; cta: string }
  brandName: string
}

export function InstagramCard({ post, brandName }: InstagramCardProps) {
  return (
    <div className="w-80 rounded-3xl border border-ink/10 bg-white overflow-hidden shadow-md">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-ink/5">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-600 to-gold-500 flex items-center justify-center flex-shrink-0">
          <span className="font-display text-xs font-black text-white">
            {brandName.slice(0, 1).toUpperCase()}
          </span>
        </div>
        <span className="font-body text-sm font-semibold text-ink truncate">{brandName}</span>
      </div>
      {/* Image placeholder */}
      <div className="w-full aspect-square bg-gradient-to-br from-teal-100 to-gold-100 flex items-center justify-center">
        <span className="font-display text-5xl font-black text-teal-700/30">
          {brandName.slice(0, 1).toUpperCase()}
        </span>
      </div>
      {/* Caption */}
      <div className="px-4 py-3 flex flex-col gap-2">
        <p className="font-body text-sm text-ink leading-relaxed line-clamp-4">{post.post_copy}</p>
        <p className="font-body text-xs text-teal-600">
          {post.hashtags.slice(0, 5).map((t) => `#${t}`).join(' ')}
        </p>
      </div>
    </div>
  )
}

export default InstagramCard
