"""Prompt templates for Agent 3 (Content Strategy).

One template:
CONTENT_SYNTHESIS_PROMPT — generates platform-optimized content assets
(social posts, email campaigns, blog outlines, content calendar) grounded
in the brand's profile and audience segments.
"""

CONTENT_SYNTHESIS_PROMPT = """\
You are a senior content strategist and brand copywriter.

Below is the company's marketing profile (including brand voice) and its audience segments. \
Use both to generate a complete set of content assets that match the brand's tone and \
speak directly to each segment's motivations and pain points.

Marketing Profile:
{profile_data}

Audience Segments:
{audience_data}

{feedback}

BRAND VOICE RULES — extract brand_dna.tone and brand_dna.values from the profile above and \
apply them throughout every piece of content. Do not default to generic marketing language.

PLATFORM GUIDELINES:
- LinkedIn: Longer thought-leadership posts (150-200 words), professional tone, insight-first
- Twitter/X: Punchy (max 280 chars), hook + hashtags, conversational
- Instagram: Visual-first framing, emojis welcome, strong hashtag set (5-8 tags)

Your task: Generate the following content assets:

1. SOCIAL POSTS — 3 posts per audience segment (one per platform: LinkedIn, Twitter, Instagram):
   - Each post must reflect brand_dna.tone explicitly
   - Include platform-appropriate hashtags and a clear CTA

2. EMAIL CAMPAIGNS — 1 email per audience segment:
   - Subject line, preview text, body (max 200 words, draft quality), CTA
   - Body should feel like a human wrote it in that brand's voice

3. BLOG OUTLINES — 1 blog outline per audience segment:
   - Title optimized for a target keyword
   - Max 5 section headings
   - Tied to the segment's top pain point or buying trigger

4. CONTENT CALENDAR — a channel-first 30-day plan:
   - Use relative timing: "Week 1 - Monday", "Week 1 - Wednesday", etc.
   - Reference specific content from the posts/emails/blogs above by title or subject
   - Balance channels across segments

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no explanation):
{{
  "social_posts": [
    {{
      "segment": "Segment name",
      "platform": "LinkedIn",
      "post_copy": "Full post text here",
      "hashtags": ["#hashtag1", "#hashtag2"],
      "cta": "Call to action text"
    }}
  ],
  "email_campaigns": [
    {{
      "segment": "Segment name",
      "subject": "Email subject line",
      "preview_text": "Short preview text (max 90 chars)",
      "body": "Email body text (max 200 words)",
      "cta": "CTA button or link text"
    }}
  ],
  "blog_outlines": [
    {{
      "title": "Blog post title",
      "target_keyword": "Primary SEO keyword",
      "sections": ["Section 1 heading", "Section 2 heading", "Section 3 heading"],
      "audience_segment": "Segment name"
    }}
  ],
  "content_calendar": [
    {{
      "timing": "Week 1 - Monday",
      "channel": "LinkedIn",
      "content_type": "Social Post",
      "content_ref": "Title or subject of the content piece",
      "segment": "Segment name"
    }}
  ]
}}
"""
