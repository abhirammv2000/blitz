"""Standalone test for Agent 4 (Sales Enablement).

Reads Agent 1's profile (test_agent1_output.json) and Agent 2's audience
segments (test_agent2_output.json), then feeds them through Agent 4's
sales synthesis to inspect output quality.

Usage:
    cd backend
    python -m agents.agent_4_sales.test_agent4
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
from agents.agent_4_sales.prompts import SALES_SYNTHESIS_PROMPT
from agents.agent_4_sales.schemas import SalesOutput


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_sales():
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

    with open(a1_output_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)
    with open(a2_output_path, "r", encoding="utf-8") as f:
        audience_data = json.load(f)

    company = profile_data.get("brand_dna", {}).get("mission", "Unknown")
    print_section(f"AGENT 4 TEST: Sales for {company[:60]}")

    profile_json = json.dumps(profile_data, indent=2)
    audience_json = json.dumps(audience_data, indent=2)

    prompt = SALES_SYNTHESIS_PROMPT.format(
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
        ),
        timeout=60.0,
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    output = SalesOutput(**data)

    # -- Email Sequences --
    print_section(f"EMAIL SEQUENCES ({len(output.email_sequences)} segments)")
    for seq in output.email_sequences:
        print(f"\n  Segment: {seq.segment}")
        for email in seq.emails:
            label = {1: "Insight", 2: "Value", 3: "Ask"}.get(email.step, f"Step {email.step}")
            print(f"    Step {email.step} ({label}) — delay: {email.delay_days}d")
            print(f"      Subject: {email.subject}")
            body_preview = email.body[:200]
            print(f"      Body:    {body_preview}{'...' if len(email.body) > 200 else ''}")

    # -- LinkedIn Templates --
    print_section(f"LINKEDIN TEMPLATES ({len(output.linkedin_templates)} segments)")
    for tmpl in output.linkedin_templates:
        print(f"\n  Segment: {tmpl.segment}")
        print(f"    Connection ({len(tmpl.connection_request)} chars): {tmpl.connection_request[:200]}")
        print(f"    Follow-up 1: {tmpl.follow_up_1[:200]}{'...' if len(tmpl.follow_up_1) > 200 else ''}")
        print(f"    Follow-up 2: {tmpl.follow_up_2[:200]}{'...' if len(tmpl.follow_up_2) > 200 else ''}")

    # -- Lead Scoring --
    print_section(f"LEAD SCORING ({len(output.lead_scoring)} tiers)")
    for tier in output.lead_scoring:
        print(f"\n  {tier.tier}: {tier.description}")
        print(f"    Signals: {', '.join(tier.signals)}")
        print(f"    Action:  {tier.action}")

    # -- Pipeline Stages --
    print_section(f"PIPELINE STAGES ({len(output.pipeline_stages)} stages)")
    for stage in output.pipeline_stages:
        print(f"\n  {stage.stage.upper()}: {stage.definition}")
        print(f"    Entry: {stage.entry_criteria}")
        print(f"    Exit:  {stage.exit_criteria}")
        print(f"    Actions: {', '.join(stage.actions)}")

    # -- Quality Checks --
    print_section("QUALITY CHECKS")

    # Segment coverage
    segments_in_emails = set(s.segment for s in output.email_sequences)
    segments_in_linkedin = set(t.segment for t in output.linkedin_templates)
    all_segments = segments_in_emails | segments_in_linkedin
    print(f"  Unique segments: {len(all_segments)}")
    for s in sorted(all_segments):
        in_e = "E" if s in segments_in_emails else "-"
        in_l = "L" if s in segments_in_linkedin else "-"
        print(f"    [{in_e}{in_l}] {s}")

    # Email sequence structure
    print(f"\n  Email steps per sequence:")
    for seq in output.email_sequences:
        steps = [e.step for e in seq.emails]
        delays = [e.delay_days for e in seq.emails]
        print(f"    {seq.segment[:40]}: steps={steps}, delays={delays}")

    # Connection request length
    print(f"\n  LinkedIn connection request lengths:")
    for tmpl in output.linkedin_templates:
        length = len(tmpl.connection_request)
        status = "OK" if length <= 300 else "OVER 300"
        print(f"    {tmpl.segment[:40]}: {length} chars ({status})")

    # Lead scoring tiers
    tiers = [t.tier for t in output.lead_scoring]
    print(f"\n  Lead scoring tiers: {tiers}")
    expected_tiers = {"Hot", "Warm", "Cold"}
    missing = expected_tiers - set(tiers)
    if missing:
        print(f"  WARNING: Missing tiers: {missing}")

    # Pipeline stages
    stages = [s.stage for s in output.pipeline_stages]
    print(f"  Pipeline stages: {stages}")

    # -- Stats --
    print_section("STATS")
    print(f"  Time:              {elapsed:.1f}s")
    print(f"  Email sequences:   {len(output.email_sequences)}")
    print(f"  LinkedIn templates: {len(output.linkedin_templates)}")
    print(f"  Lead scoring tiers: {len(output.lead_scoring)}")
    print(f"  Pipeline stages:   {len(output.pipeline_stages)}")

    # Save output
    outfile = os.path.join(os.path.dirname(__file__), "test_agent4_output.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {outfile}")

    return output


if __name__ == "__main__":
    asyncio.run(test_sales())
