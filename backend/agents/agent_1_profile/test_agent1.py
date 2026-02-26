"""Standalone test for Agent 1 (Marketing Profile Creator).

Reads Agent 0's saved output (test_agent0_output.json) and feeds it through
Agent 1's profile synthesis to inspect output quality.

Usage:
    cd backend
    python -m agents.agent_1_profile.test_agent1
"""

import asyncio
import json
import os
import sys
import time
import re

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(override=True)

import litellm
from agents.agent_1_profile.prompts import PROFILE_SYNTHESIS_PROMPT
from agents.agent_1_profile.schemas import MarketingProfile


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_profile():
    # Load Agent 0's output as the research input
    a0_output_path = os.path.join(
        os.path.dirname(__file__), "..", "agent_0_research", "test_agent0_output.json"
    )
    if not os.path.exists(a0_output_path):
        print(f"ERROR: No Agent 0 output found at {a0_output_path}")
        print("Run Agent 0 test first: python -m agents.agent_0_research.test_agent0")
        return

    with open(a0_output_path, "r", encoding="utf-8") as f:
        research_data = json.load(f)

    company = research_data.get("company_name", "Unknown")
    print_section(f"AGENT 1 TEST: Profile for {company}")

    research_json = json.dumps(research_data, indent=2)

    prompt = PROFILE_SYNTHESIS_PROMPT.format(
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
            temperature=0.3,
        ),
        timeout=60.0,
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    profile = MarketingProfile(**data)

    # Display results
    print_section("BRAND DNA")
    print(f"  Mission:       {profile.brand_dna.mission}")
    print(f"  Values:        {profile.brand_dna.values}")
    print(f"  Tone:          {profile.brand_dna.tone}")
    print(f"  Voice Example: {profile.brand_dna.voice_example}")
    print(f"  Visual Style:  {profile.brand_dna.visual_style}")

    print_section("POSITIONING STATEMENT")
    print(f"  {profile.positioning_statement}")

    print_section(f"TARGET AUDIENCES ({len(profile.target_audiences)})")
    for i, aud in enumerate(profile.target_audiences, 1):
        print(f"  {i}. {aud.segment}")
        print(f"     Pain points:       {aud.pain_points}")
        print(f"     Decision drivers:  {aud.decision_drivers}")
        print()

    print_section(f"USPs ({len(profile.usps)})")
    for i, usp in enumerate(profile.usps, 1):
        print(f"  {i}. {usp}")

    print_section(f"COMPETITIVE EDGES ({len(profile.competitive_edges)})")
    for i, edge in enumerate(profile.competitive_edges, 1):
        print(f"  {i}. vs {edge.competitor}")
        print(f"     Advantage:     {edge.advantage}")
        print(f"     Vulnerability: {edge.vulnerability}")
        print()

    print_section(f"MESSAGING PILLARS ({len(profile.messaging_pillars)})")
    for i, pillar in enumerate(profile.messaging_pillars, 1):
        print(f"  {i}. {pillar}")

    print_section(f"MARKETING GAPS ({len(profile.marketing_gaps)})")
    for i, gap in enumerate(profile.marketing_gaps, 1):
        print(f"  {i}. GAP:      {gap.gap}")
        print(f"     EVIDENCE:  {gap.evidence}")
        print(f"     REC:       {gap.recommendation}")
        print()

    print_section("STATS")
    print(f"  Time:               {elapsed:.1f}s")
    print(f"  Target audiences:   {len(profile.target_audiences)}")
    print(f"  USPs:               {len(profile.usps)}")
    print(f"  Competitive edges:  {len(profile.competitive_edges)}")
    print(f"  Marketing gaps:     {len(profile.marketing_gaps)}")

    # Save output
    outfile = os.path.join(os.path.dirname(__file__), "test_agent1_output.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {outfile}")

    return profile


if __name__ == "__main__":
    asyncio.run(test_profile())
