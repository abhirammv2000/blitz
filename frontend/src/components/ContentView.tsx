import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'

// TypeScript interfaces matching backend Pydantic schemas
export interface SocialPost {
  platform: string
  post_copy: string
  hashtags: string[]
  cta: string
}

export interface EmailCampaign {
  subject: string
  preview_text: string
  body: string
  cta: string
  segment: string
}

export interface BlogOutlineSection {
  heading: string
  key_points: string[]
}

export interface BlogOutline {
  title: string
  target_keyword: string
  sections: BlogOutlineSection[]
}

export interface ContentCalendarEntry {
  timing: string
  channel: string
  content_type: string
  segment: string
}

export interface ContentOutput {
  social_posts: SocialPost[]
  email_campaigns: EmailCampaign[]
  blog_outlines: BlogOutline[]
  content_calendar: ContentCalendarEntry[]
}

interface ContentViewProps {
  output: ContentOutput
}

const PLATFORM_COLORS: Record<string, string> = {
  LinkedIn: 'bg-blue-600/10 border-blue-500/20 text-blue-300',
  Twitter: 'bg-sky-600/10 border-sky-500/20 text-sky-300',
  Instagram: 'bg-pink-600/10 border-pink-500/20 text-pink-300',
}

export default function ContentView({ output }: ContentViewProps) {
  const { social_posts = [], email_campaigns = [], blog_outlines = [], content_calendar = [] } = output

  // Group social posts by platform
  const postsByPlatform = social_posts.reduce<Record<string, SocialPost[]>>((acc, post) => {
    const platform = post.platform ?? 'Other'
    acc[platform] = acc[platform] ?? []
    acc[platform].push(post)
    return acc
  }, {})

  return (
    <div className="rounded-2xl border border-white/8 bg-white/3 overflow-hidden">
      <TabGroup>
        <TabList className="flex border-b border-white/8 overflow-x-auto">
          {['Social Posts', 'Emails', 'Blog Outlines', 'Calendar'].map((tab) => (
            <Tab
              key={tab}
              className="flex-1 min-w-max px-4 py-3 text-sm font-medium text-zinc-500 hover:text-zinc-300 data-[selected]:text-white data-[selected]:bg-white/5 data-[selected]:border-b-2 data-[selected]:border-violet-500 transition-colors outline-none"
            >
              {tab}
            </Tab>
          ))}
        </TabList>

        <TabPanels>
          {/* Social Posts Tab */}
          <TabPanel className="p-6 flex flex-col gap-6">
            {Object.keys(postsByPlatform).length === 0 && (
              <p className="text-sm text-zinc-600 italic">No social posts generated.</p>
            )}
            {Object.entries(postsByPlatform).map(([platform, posts]) => (
              <div key={platform}>
                <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-3">{platform}</p>
                <div className="flex flex-col gap-3">
                  {posts.map((post, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3"
                    >
                      <p className="text-sm text-zinc-200 leading-relaxed">{post.post_copy}</p>
                      {post.hashtags?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {post.hashtags.map((tag, j) => (
                            <span
                              key={j}
                              className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${PLATFORM_COLORS[platform] ?? 'bg-violet-600/10 border-violet-500/20 text-violet-300'}`}
                            >
                              #{tag.replace(/^#/, '')}
                            </span>
                          ))}
                        </div>
                      )}
                      {post.cta && (
                        <p className="text-xs text-zinc-500">
                          CTA: <span className="text-zinc-300">{post.cta}</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </TabPanel>

          {/* Email Campaigns Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {email_campaigns.length === 0 && (
              <p className="text-sm text-zinc-600 italic">No email campaigns generated.</p>
            )}
            {email_campaigns.map((email, i) => (
              <div
                key={i}
                className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3"
              >
                {email.segment && (
                  <span className="inline-flex self-start rounded-full bg-violet-500/10 border border-violet-500/20 px-2.5 py-0.5 text-xs text-violet-300 font-medium">
                    {email.segment}
                  </span>
                )}
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Subject</p>
                  <p className="text-sm font-semibold text-white">{email.subject}</p>
                </div>
                {email.preview_text && (
                  <p className="text-xs text-zinc-500 italic">{email.preview_text}</p>
                )}
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Body</p>
                  <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">{email.body}</p>
                </div>
                {email.cta && (
                  <div className="self-start rounded-xl bg-emerald-600/10 border border-emerald-500/20 px-4 py-2">
                    <p className="text-xs text-emerald-400 font-semibold">{email.cta}</p>
                  </div>
                )}
              </div>
            ))}
          </TabPanel>

          {/* Blog Outlines Tab */}
          <TabPanel className="p-6 flex flex-col gap-4">
            {blog_outlines.length === 0 && (
              <p className="text-sm text-zinc-600 italic">No blog outlines generated.</p>
            )}
            {blog_outlines.map((outline, i) => (
              <div
                key={i}
                className="rounded-xl border border-white/8 bg-white/3 p-4 flex flex-col gap-3"
              >
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Title</p>
                  <p className="text-sm font-semibold text-white">{outline.title}</p>
                </div>
                {outline.target_keyword && (
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-1">Target Keyword</p>
                    <span className="inline-flex rounded-full bg-amber-500/10 border border-amber-500/20 px-2.5 py-0.5 text-xs text-amber-300 font-medium">
                      {outline.target_keyword}
                    </span>
                  </div>
                )}
                {outline.sections?.length > 0 && (
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium mb-2">Sections</p>
                    <div className="flex flex-col gap-2">
                      {outline.sections.map((section, j) => (
                        <div key={j} className="rounded-lg border border-white/6 bg-white/2 px-3 py-2">
                          <p className="text-xs font-semibold text-zinc-300 mb-1">{section.heading}</p>
                          {section.key_points?.length > 0 && (
                            <ul className="flex flex-col gap-0.5">
                              {section.key_points.map((pt, k) => (
                                <li key={k} className="text-xs text-zinc-500 flex items-start gap-1.5">
                                  <span className="text-violet-400 flex-shrink-0 mt-0.5">-</span>
                                  {pt}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </TabPanel>

          {/* Content Calendar Tab */}
          <TabPanel className="p-6">
            {content_calendar.length === 0 && (
              <p className="text-sm text-zinc-600 italic">No calendar entries generated.</p>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/8">
                    <th className="text-left text-xs text-zinc-500 uppercase tracking-widest font-medium pb-3 pr-4">Timing</th>
                    <th className="text-left text-xs text-zinc-500 uppercase tracking-widest font-medium pb-3 pr-4">Channel</th>
                    <th className="text-left text-xs text-zinc-500 uppercase tracking-widest font-medium pb-3 pr-4">Content Type</th>
                    <th className="text-left text-xs text-zinc-500 uppercase tracking-widest font-medium pb-3">Segment</th>
                  </tr>
                </thead>
                <tbody>
                  {content_calendar.map((entry, i) => (
                    <tr key={i} className="border-b border-white/4 last:border-0">
                      <td className="py-2.5 pr-4 text-zinc-400 text-xs">{entry.timing}</td>
                      <td className="py-2.5 pr-4 text-zinc-300 text-xs">{entry.channel}</td>
                      <td className="py-2.5 pr-4 text-zinc-300 text-xs">{entry.content_type}</td>
                      <td className="py-2.5 text-zinc-500 text-xs">{entry.segment}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  )
}
