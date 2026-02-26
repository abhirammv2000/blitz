"""Standalone test for Agent 5 (Paid Ads).

Reads Agent 1's profile (test_agent1_output.json) and Agent 2's audience
segments (test_agent2_output.json), then feeds them through Agent 5's
ad synthesis to inspect output quality.

Usage:
    cd backend
    python -m agents.agent_5_ads.test_agent5
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
from agents.agent_5_ads.prompts import ADS_SYNTHESIS_PROMPT
from agents.agent_5_ads.schemas import AdsOutput


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_ads():
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
    print_section(f"AGENT 5 TEST: Ads for {company[:60]}")

    profile_json = json.dumps(profile_data, indent=2)
    audience_json = json.dumps(audience_data, indent=2)

    prompt = ADS_SYNTHESIS_PROMPT.format(
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
            temperature=0.5,
        ),
        timeout=60.0,
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    output = AdsOutput(**data)

    # -- Ad Copies --
    print_section(f"AD COPIES ({len(output.ad_copies)} total)")
    for i, ad in enumerate(output.ad_copies, 1):
        print(f"  {i}. [{ad.platform}] Segment: {ad.segment}")
        print(f"     Headline ({len(ad.headline)} chars): {ad.headline}")
        body_preview = ad.body[:200]
        print(f"     Body: {body_preview}{'...' if len(ad.body) > 200 else ''}")
        print(f"     CTA:  {ad.cta}")
        print()

    # -- Ad Visuals --
    print_section(f"AD VISUALS ({len(output.ad_visuals)} total)")
    for i, vis in enumerate(output.ad_visuals, 1):
        print(f"  {i}. [{vis.platform}] Segment: {vis.segment}")
        print(f"     Concept: {vis.visual_concept[:150]}")
        print(f"     Colors:  {', '.join(vis.color_palette)}")
        print(f"     Prompt:  {vis.image_prompt[:150]}{'...' if len(vis.image_prompt) > 150 else ''}")
        print()

    # -- A/B Variations --
    print_section(f"A/B VARIATIONS ({len(output.ab_variations)} total)")
    for i, ab in enumerate(output.ab_variations, 1):
        print(f"  {i}. [{ab.variant_label}] Ref: {ab.ad_copy_ref}")
        print(f"     Headline: {ab.headline}")
        print(f"     Hypothesis: {ab.test_hypothesis}")
        print(f"     Prompt: {ab.image_prompt[:120]}{'...' if len(ab.image_prompt) > 120 else ''}")
        print()

    # -- Quality Checks --
    print_section("QUALITY CHECKS")

    # Segment coverage
    segments_in_copies = set(a.segment for a in output.ad_copies)
    segments_in_visuals = set(v.segment for v in output.ad_visuals)
    all_segments = segments_in_copies | segments_in_visuals
    print(f"  Unique segments: {len(all_segments)}")
    for s in sorted(all_segments):
        in_c = "C" if s in segments_in_copies else "-"
        in_v = "V" if s in segments_in_visuals else "-"
        print(f"    [{in_c}{in_v}] {s}")

    # Platform coverage
    platforms_in_copies = set(a.platform for a in output.ad_copies)
    platforms_in_visuals = set(v.platform for v in output.ad_visuals)
    print(f"\n  Platforms in copies:  {sorted(platforms_in_copies)}")
    print(f"  Platforms in visuals: {sorted(platforms_in_visuals)}")

    # A/B variant labels
    labels = set(ab.variant_label for ab in output.ab_variations)
    print(f"  A/B variant labels: {sorted(labels)}")

    # Headline length checks (Google Ads should be ~30 chars)
    print(f"\n  Headline lengths:")
    for ad in output.ad_copies:
        status = ""
        if ad.platform == "Google Ads" and len(ad.headline) > 30:
            status = " (OVER 30 for Google)"
        print(f"    {ad.platform[:12]:12} | {ad.segment[:35]:35} | {len(ad.headline):3} chars{status}")

    # Image prompts present
    prompts_missing = [v for v in output.ad_visuals if not v.image_prompt]
    ab_prompts_missing = [ab for ab in output.ab_variations if not ab.image_prompt]
    print(f"\n  Visuals missing image_prompt: {len(prompts_missing)}")
    print(f"  A/B vars missing image_prompt: {len(ab_prompts_missing)}")

    # -- Stats --
    print_section("STATS")
    print(f"  Time:           {elapsed:.1f}s")
    print(f"  Ad copies:      {len(output.ad_copies)}")
    print(f"  Ad visuals:     {len(output.ad_visuals)}")
    print(f"  A/B variations: {len(output.ab_variations)}")

    # Save output
    outfile = os.path.join(os.path.dirname(__file__), "test_agent5_output.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {outfile}")

    return output


if __name__ == "__main__":
    asyncio.run(test_ads())
