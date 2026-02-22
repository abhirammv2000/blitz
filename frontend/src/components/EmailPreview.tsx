interface EmailPreviewProps {
  email: { subject: string; preview_text: string; body: string; cta: string; segment: string }
}

export function EmailPreview({ email }: EmailPreviewProps) {
  return (
    <div className="max-w-lg rounded-2xl border border-ink/10 bg-white shadow-md overflow-hidden">
      {/* Email metadata */}
      <div className="bg-cream-dark px-6 py-4 border-b border-ink/8">
        <p className="font-body text-xs text-ink-faint uppercase tracking-widest mb-1">Subject</p>
        <p className="font-display text-lg font-bold text-ink">{email.subject}</p>
        <p className="font-body text-xs text-ink-muted mt-1">{email.preview_text}</p>
      </div>
      {/* Email body */}
      <div className="px-6 py-5">
        <p className="font-body text-sm text-ink leading-relaxed whitespace-pre-line">{email.body}</p>
        {/* CTA button */}
        <div className="mt-5">
          <button className="px-5 py-2.5 rounded-xl bg-teal-600 text-white font-body font-semibold text-sm hover:bg-teal-700 transition-colors">
            {email.cta}
          </button>
        </div>
      </div>
    </div>
  )
}

export default EmailPreview
