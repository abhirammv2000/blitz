"""Standalone test for Agent 2 (Audience Identifier).

Reads Agent 1's saved output (test_agent1_output.json) and feeds it through
Agent 2's audience synthesis to inspect output quality.

Usage:
    cd backend
    python -m agents.agent_2_audience.test_agent2
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
from agents.agent_2_audience.prompts import AUDIENCE_SYNTHESIS_PROMPT
from agents.agent_2_audience.schemas import AudienceOutput


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_audience():
    a0_output_path = os.path.join(
        os.path.dirname(__file__), "..", "agent_0_research", "test_agent0_output.json"
    )
    a1_output_path = os.path.join(
        os.path.dirname(__file__), "..", "agent_1_profile", "test_agent1_output.json"
    )
    if not os.path.exists(a1_output_path):
        print(f"ERROR: No Agent 1 output found at {a1_output_path}")
        print("Run Agent 1 test first: python -m agents.agent_1_profile.test_agent1")
        return

    with open(a1_output_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    research_data = {}
    if os.path.exists(a0_output_path):
        with open(a0_output_path, "r", encoding="utf-8") as f:
            research_data = json.load(f)

    company = research_data.get("company_name", "Unknown")
    print_section(f"AGENT 2 TEST: Audiences for {company}")

    profile_json = json.dumps(profile_data, indent=2)
    research_json = json.dumps(research_data, indent=2)

    prompt = AUDIENCE_SYNTHESIS_PROMPT.format(
        profile_data=profile_json,
        research_data=research_json,
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
    output = AudienceOutput(**data)

    for i, seg in enumerate(output.segments, 1):
        print_section(f"SEGMENT {i}: {seg.name} [{seg.fit_label}]")

        print(f"  Demographics:")
        demo = seg.demographics
        print(f"    Age:        {demo.get('age_range', '?')}")
        print(f"    Titles:     {demo.get('job_titles', [])}")
        print(f"    Co. sizes:  {demo.get('company_sizes', [])}")
        print(f"    Industries: {demo.get('industries', [])}")

        print(f"  Psychographics:")
        psych = seg.psychographics
        print(f"    Values:     {psych.get('values', [])}")
        print(f"    Goals:      {psych.get('goals', [])}")
        print(f"    Frustr.:    {psych.get('frustrations', [])}")

        print(f"  Pain points:  {seg.pain_points}")
        print(f"  Buy triggers: {seg.buying_triggers}")
        print(f"  Channels:     {seg.active_channels}")

        print(f"  Synthetic:")
        syn = seg.synthetic_attributes
        print(f"    Deal size:   {syn.get('avg_deal_size', '?')}")
        print(f"    Sales cycle: {syn.get('sales_cycle_days', '?')} days")
        print(f"    LTV:         {syn.get('ltv_estimate', '?')}")
        print(f"    Persona:     {syn.get('persona_name', '?')}")

        print(f"  Reasoning: {seg.reasoning[:200]}")
        print()

    print_section("STATS")
    print(f"  Time:      {elapsed:.1f}s")
    print(f"  Segments:  {len(output.segments)}")
    fit_counts = {}
    for s in output.segments:
        fit_counts[s.fit_label] = fit_counts.get(s.fit_label, 0) + 1
    print(f"  Fit dist:  {fit_counts}")

    outfile = os.path.join(os.path.dirname(__file__), "test_agent2_output.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {outfile}")

    return output


if __name__ == "__main__":
    asyncio.run(test_audience())
