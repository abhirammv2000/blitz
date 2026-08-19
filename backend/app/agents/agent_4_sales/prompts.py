"""Prompt templates for Agent 4 (Sales Enablement).

One template:
SALES_SYNTHESIS_PROMPT — generates multi-touch email sequences, LinkedIn DM
templates, lead scoring tiers, and pipeline stage definitions for each
audience segment, using a consultative voice grounded in the brand profile.
"""

SALES_SYNTHESIS_PROMPT = """\
You are a senior sales strategist and outreach copywriter.

Below is the company's research dossier, marketing profile, and audience segments. Use ALL THREE to generate \
a complete sales enablement toolkit — email sequences, LinkedIn DM templates, lead scoring \
criteria, and pipeline stage definitions.

Research Dossier (competitors, press, funding, AEO):
{research_data}

Marketing Profile:
{profile_data}

Audience Segments:
{audience_data}

{feedback}

GROUNDING RULES — every piece of outreach MUST reference specific facts from the Research Dossier above:
- Email Insight step must reference a real competitor, press item, or industry data point from the research
- LinkedIn connection request must reference an industry trend or company milestone — NOT a fabricated personal interaction ("saw your post", "loved your talk")
- Lead scoring signals must reference company-specific product pages, competitor triggers, and segment buying triggers from the audience data
- Pipeline stages should note segment-specific sales cycle length from audience data

CONSULTATIVE VOICE RULES — extract brand_dna.tone and brand_dna.values from the profile above. \
Every piece of outreach must lead with genuine insight before mentioning value, and never \
open with a pitch or ask.

EMAIL SEQUENCE RULES:
- Exactly 3 emails per audience segment following the Insight -> Value -> Ask progression:
  - Step 1 (Insight): Share a relevant observation or industry trend. No product mention.
  - Step 2 (Value): Connect the insight to a specific benefit or use case. Soft reference to the product.
  - Step 3 (Ask): Clear, low-friction ask (demo, quick call, or resource). Confident, not pushy.
- Email bodies should read as written by a thoughtful human, not a bot.
- delay_days for step 1 = 0, step 2 = 3-5 days, step 3 = 4-7 days after step 2.

LINKEDIN DM RULES:
- Connection request: Max 300 chars. Mention a shared context or genuine observation. No pitch.
- Follow-up 1: Delivers value (article, insight, stat). Casual, friendly.
- Follow-up 2: Gentle ask or resource share. Respects their time.

LEAD SCORING RULES — define exactly 3 tiers:
- Hot: Ready to buy. Strong engagement signals. Prioritize immediately.
- Warm: Interested but not yet ready. Nurture with value content.
- Cold: Low engagement. Long-term relationship building or re-engagement play.

PIPELINE STAGES — define exactly 4 stages in order:
- prospect: Identified but not yet contacted
- contacted: Outreach sent, awaiting response
- engaged: Two-way conversation started
- converted: Demo booked or deal initiated

Your task: Generate the full sales enablement toolkit.

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no explanation):
{{
  "email_sequences": [
    {{
      "segment": "Segment name",
      "emails": [
        {{
          "step": 1,
          "subject": "Email subject line",
          "body": "Email body text",
          "delay_days": 0
        }},
        {{
          "step": 2,
          "subject": "Email subject line",
          "body": "Email body text",
          "delay_days": 4
        }},
        {{
          "step": 3,
          "subject": "Email subject line",
          "body": "Email body text",
          "delay_days": 5
        }}
      ]
    }}
  ],
  "linkedin_templates": [
    {{
      "segment": "Segment name",
      "connection_request": "Short connection request message",
      "follow_up_1": "First follow-up message delivering value",
      "follow_up_2": "Second follow-up with gentle ask"
    }}
  ],
  "lead_scoring": [
    {{
      "tier": "Hot",
      "description": "Description of what makes a lead Hot",
      "signals": ["Signal 1", "Signal 2", "Signal 3"],
      "action": "Recommended action for Hot leads"
    }},
    {{
      "tier": "Warm",
      "description": "Description of what makes a lead Warm",
      "signals": ["Signal 1", "Signal 2"],
      "action": "Recommended action for Warm leads"
    }},
    {{
      "tier": "Cold",
      "description": "Description of what makes a lead Cold",
      "signals": ["Signal 1", "Signal 2"],
      "action": "Recommended action for Cold leads"
    }}
  ],
  "pipeline_stages": [
    {{
      "stage": "prospect",
      "definition": "Stage definition",
      "entry_criteria": "What triggers entry to this stage",
      "exit_criteria": "What triggers exit to next stage",
      "actions": ["Action 1", "Action 2"]
    }},
    {{
      "stage": "contacted",
      "definition": "Stage definition",
      "entry_criteria": "What triggers entry to this stage",
      "exit_criteria": "What triggers exit to next stage",
      "actions": ["Action 1", "Action 2"]
    }},
    {{
      "stage": "engaged",
      "definition": "Stage definition",
      "entry_criteria": "What triggers entry to this stage",
      "exit_criteria": "What triggers exit to next stage",
      "actions": ["Action 1", "Action 2"]
    }},
    {{
      "stage": "converted",
      "definition": "Stage definition",
      "entry_criteria": "What triggers entry to this stage",
      "exit_criteria": "Deal initiated or demo booked",
      "actions": ["Action 1", "Action 2"]
    }}
  ]
}}
"""
