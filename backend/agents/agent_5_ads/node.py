"""LangGraph node function for Agent 5 (Paid Ads).

Implements the HITL reject loop pattern:
- Reads Agent 1's marketing profile and Agent 2's audience segments from ChromaDB
- Calls run_ads() to generate platform-specific ad copy via GPT-4o
- Generates DALL-E 3 images for each A/B variation concurrently via asyncio.gather()
- Interrupts with AdsOutput for human review
- Handles approve / edit / override / reject decisions
- On reject: loops back with feedback to refine ad creative
- Stores final HITL decision in ChromaDB for downstream reference

Why async: litellm.acompletion() and aimage_generation() are awaited; DALL-E 3
image generation is parallelized via asyncio.gather() for throughput.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import litellm
from langgraph.types import interrupt

from agents.agent_5_ads.prompts import ADS_SYNTHESIS_PROMPT, build_image_prompt
from agents.agent_5_ads.schemas import AdsOutput
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def generate_ad_image(prompt: str) -> str | None:
    """Generate a single DALL-E 3 image for an ad variation.

    Uses asyncio.wait_for with a 60s timeout — DALL-E 3 is slower than text
    completion. Returns None on any failure so the pipeline continues without
    blocking on a single failed image.

    Args:
        prompt: DALL-E 3 ready prompt string.

    Returns:
        Public image URL string, or None if generation fails.
    """
    try:
        response = await asyncio.wait_for(
            litellm.aimage_generation(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="url",
                api_key=os.environ.get("OPENAI_API_KEY", ""),
            ),
            timeout=60.0,
        )
        return response.data[0].url
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning("DALL-E 3 image gen failed: %s", e)
        return None


async def run_ads(run_id: str, feedback: str | None = None) -> AdsOutput:
    """Run the ad creative synthesis LLM call for a given run_id.

    Step 1: Reads profile + audience from ChromaDB.
    Step 2: Calls GPT-4o to generate ad copy JSON (no images yet).
    Step 3: Parses JSON into AdsOutput.
    Step 4: Generates DALL-E 3 images for all A/B variations concurrently.

    Args:
        run_id: Pipeline run identifier — used to fetch context from ChromaDB.
        feedback: Optional reject feedback from HITL loop to guide refinement.

    Returns:
        AdsOutput with ad copies, visuals, and A/B variations (with image URLs).
    """
    # Read upstream agent outputs from ChromaDB
    profile_raw = get_agent_output(run_id, "profile")
    if profile_raw is None:
        logger.warning("Agent 5: no profile found in ChromaDB for run_id=%s", run_id)
        profile_data = "{}"
    else:
        profile_data = profile_raw

    audience_raw = get_agent_output(run_id, "audience")
    if audience_raw is None:
        logger.warning("Agent 5: no audience found in ChromaDB for run_id=%s", run_id)
        audience_data = "{}"
    else:
        audience_data = audience_raw

    # Build feedback instruction
    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised ad creative."
        if feedback
        else ""
    )

    prompt = ADS_SYNTHESIS_PROMPT.format(
        profile_data=profile_data,
        audience_data=audience_data,
        feedback=feedback_instruction,
    )

    # Step 1: Generate ad copy via GPT-4o (no images yet)
    response = await asyncio.wait_for(
        litellm.acompletion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=0.5,
        ),
        timeout=45.0,
    )

    content = response.choices[0].message.content or "{}"

    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    output = AdsOutput(**data)

    # Step 2: Generate DALL-E 3 images for all A/B variations concurrently
    # Extract brand tone from profile for richer image prompts
    try:
        profile_dict = json.loads(profile_data)
        brand_tone = profile_dict.get("brand_voice", {}).get("tone", "professional")
    except (json.JSONDecodeError, AttributeError):
        brand_tone = "professional"

    # Build image prompts for each A/B variation
    image_prompts = []
    for variation in output.ab_variations:
        # Get matching visual's color palette if available, else default
        matching_visual = next(
            (v for v in output.ad_visuals if variation.ad_copy_ref in (v.segment + " " + v.platform)),
            None,
        )
        color_palette = matching_visual.color_palette if matching_visual else []
        image_prompts.append(
            build_image_prompt(variation.image_prompt, brand_tone, color_palette)
        )

    # Parallel image generation for all A/B variations
    image_urls = await asyncio.gather(*[generate_ad_image(p) for p in image_prompts])
    for i, url in enumerate(image_urls):
        output.ab_variations[i].image_url = url

    return output


async def agent_5_ads_node(state: BlitzState) -> dict:
    """Ad Creative Generator node: produces platform-specific ads with AI images.

    HITL loop pattern:
    1. Run ad synthesis (with optional reject feedback)
    2. Interrupt — surface AdsOutput to frontend for human review
    3. On resume: check decision action
       - "approve": accept output as-is, break
       - "edit": merge user edits into output, break
       - "override": replace output with user-supplied data, break
       - "reject": set feedback, loop back to step 1

    After loop: stores the final output and HITL decision in ChromaDB.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step, ads_output, and approved flag.
    """
    run_id: str = state.get("run_id", "")

    feedback: str | None = None
    final_output: AdsOutput | None = None
    decision: dict = {}

    while True:
        # Run (or re-run with feedback) the ad creative synthesis
        output = await run_ads(run_id, feedback)

        # Interrupt: surface AdsOutput to frontend for HITL review
        decision = interrupt({
            "step": 5,
            "agent": "agent_5_ads",
            "output": output.model_dump(),
            "action": "approve | edit | reject | override",
        })

        action = decision.get("action", "approve")

        if action == "approve":
            final_output = output
            break

        elif action == "edit":
            # Merge user edits into the output
            edits = decision.get("data", {})
            final_output = AdsOutput(**{**output.model_dump(), **edits})
            break

        elif action == "override":
            # Replace output entirely with user-supplied data
            final_output = AdsOutput(**decision["data"])
            break

        elif action == "reject":
            # Loop back with feedback to refine ad creative
            feedback = decision.get("feedback", "")
            continue

        else:
            # Unknown action — treat as approve
            final_output = output
            break

    # Store ads output and HITL decision in ChromaDB for downstream agents
    store_agent_output(run_id, "ads", json.dumps(final_output.model_dump()))
    store_agent_output(run_id, "ads_decision", json.dumps(decision))

    return {
        "current_step": 5,
        "ads_output": final_output.model_dump(),
        "approved": True,
    }
