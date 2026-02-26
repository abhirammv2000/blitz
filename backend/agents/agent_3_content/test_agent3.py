"""Standalone test for Agent 3 (Content Strategist).

Reads Agent 1's profile (test_agent1_output.json) and Agent 2's audience
segments (test_agent2_output.json), then feeds them through Agent 3's
content synthesis to inspect output quality.

Usage:
    cd backend
    python -m agents.agent_3_content.test_agent3
"""

import asyncio
import json
import os
import sys
import time
import re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(override=True)

import litellm
from agents.agent_3_content.prompts import CONTENT_SYNTHESIS_PROMPT
from agents.agent_3_content.schemas import ContentOutput


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_content():
    a0_output_path = os.path.join(
        os.path.dirname(__file__), "..", "agent_0_research", "test_agent0_output.json"
    )
    a1_output_path = os.path.join(
        os.path.dirname(__file__), "..", "agent_1_profile", "test_agent1_output.json"
    )
    a2_output_path = os.path.join(
        os.path.dirname(__file__), "..", "agent_2_audience", "test_agent2_output.json"
    )

    if not os.path.exists(a1_output_path):
        print(f"ERROR: No Agent 1 output found at {a1_output_path}")
        print("Run Agent 1 test first: python -m agents.agent_1_profile.test_agent1")
        return
    if not os.path.exists(a2_output_path):
        print(f"ERROR: No Agent 2 output found at {a2_output_path}")
        print("Run Agent 2 test first: python -m agents.agent_2_audience.test_agent2")
        return

    research_data = {}
    if os.path.exists(a0_output_path):
        with open(a0_output_path, "r", encoding="utf-8") as f:
            research_data = json.load(f)

    with open(a1_output_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)
    with open(a2_output_path, "r", encoding="utf-8") as f:
        audience_data = json.load(f)

    company = research_data.get("company_name", profile_data.get("brand_dna", {}).get("mission", "Unknown"))
    print_section(f"AGENT 3 TEST: Content for {company}")

    research_json = json.dumps(research_data, indent=2)
    profile_json = json.dumps(profile_data, indent=2)
    audience_json = json.dumps(audience_data, indent=2)

    prompt = CONTENT_SYNTHESIS_PROMPT.format(
        research_data=research_json,
        profile_data=profile_json,
        audience_data=audience_json,
        feedback="",
    )

    print(f"  Prompt length: {len(prompt)} chars")

    start = time.time()
    response = await asyncio.wait_for(
        litellm.acompletion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=0.4,
            max_tokens=8000,
        ),
        timeout=90.0,
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    output = ContentOutput(**data)

    # -- Social Posts --
    print_section(f"SOCIAL POSTS ({len(output.social_posts)} total)")
    for i, post in enumerate(output.social_posts, 1):
        print(f"  {i}. [{post.platform}] Segment: {post.segment}")
        copy_preview = post.post_copy[:200]
        print(f"     Copy: {copy_preview}{'...' if len(post.post_copy) > 200 else ''}")
        print(f"     Tags: {', '.join(post.hashtags[:5])}")
        print(f"     CTA:  {post.cta}")
        print()

    # -- Email Campaigns --
    print_section(f"EMAIL CAMPAIGNS ({len(output.email_campaigns)} total)")
    for i, email in enumerate(output.email_campaigns, 1):
        print(f"  {i}. Segment: {email.segment}")
        print(f"     Subject: {email.subject}")
        print(f"     Preview: {email.preview_text}")
        body_preview = email.body[:300]
        print(f"     Body:    {body_preview}{'...' if len(email.body) > 300 else ''}")
        print(f"     CTA:     {email.cta}")
        print()

    # -- Blog Outlines --
    print_section(f"BLOG OUTLINES ({len(output.blog_outlines)} total)")
    for i, blog in enumerate(output.blog_outlines, 1):
        print(f"  {i}. \"{blog.title}\"")
        print(f"     Keyword:  {blog.target_keyword}")
        print(f"     Segment:  {blog.audience_segment}")
        print(f"     Sections:")
        for j, sec in enumerate(blog.sections, 1):
            print(f"       {j}. {sec}")
        print()

    # -- Content Calendar --
    print_section(f"CONTENT CALENDAR ({len(output.content_calendar)} entries)")
    for entry in output.content_calendar:
        print(f"  {entry.timing:<22} | {entry.channel:<12} | {entry.content_type:<15} | {entry.segment}")
        print(f"  {'':22}   Ref: {entry.content_ref[:80]}")
        print()

    # -- Quality Checks --
    print_section("QUALITY CHECKS")

    # Check segment coverage
    segments_in_posts = set(p.segment for p in output.social_posts)
    segments_in_emails = set(e.segment for e in output.email_campaigns)
    segments_in_blogs = set(b.audience_segment for b in output.blog_outlines)
    segments_in_cal = set(c.segment for c in output.content_calendar)
    all_segments = segments_in_posts | segments_in_emails | segments_in_blogs | segments_in_cal
    print(f"  Unique segments covered: {len(all_segments)}")
    for s in sorted(all_segments):
        in_posts = "P" if s in segments_in_posts else "-"
        in_emails = "E" if s in segments_in_emails else "-"
        in_blogs = "B" if s in segments_in_blogs else "-"
        in_cal = "C" if s in segments_in_cal else "-"
        print(f"    [{in_posts}{in_emails}{in_blogs}{in_cal}] {s}")

    # Check platform coverage in social posts
    platforms = set(p.platform for p in output.social_posts)
    print(f"\n  Platforms in social: {sorted(platforms)}")

    # Check calendar spread
    weeks = set()
    for entry in output.content_calendar:
        week = entry.timing.split("-")[0].strip() if "-" in entry.timing else entry.timing
        weeks.add(week)
    print(f"  Calendar weeks:     {sorted(weeks)}")

    # -- Stats --
    print_section("STATS")
    print(f"  Time:            {elapsed:.1f}s")
    print(f"  Social posts:    {len(output.social_posts)}")
    print(f"  Email campaigns: {len(output.email_campaigns)}")
    print(f"  Blog outlines:   {len(output.blog_outlines)}")
    print(f"  Calendar entries: {len(output.content_calendar)}")

    # Save output
    outfile = os.path.join(os.path.dirname(__file__), "test_agent3_output.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {outfile}")

    return output


if __name__ == "__main__":
    asyncio.run(test_content())
