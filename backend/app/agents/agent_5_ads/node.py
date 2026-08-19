"""LangGraph node function for Agent 5 (Paid Ads).

Reads profile and audience segments from ChromaDB, generates ad creative
via GPT-4o, synthesizes image prompts, and stores the result.

Image generation is user-triggered via POST /ads/{run_id}/generate-image endpoint
(capped at 3 per run). Users edit prompts in the UI before generating.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

import litellm

from app.agents.agent_5_ads.prompts import ADS_SYNTHESIS_PROMPT, IMAGE_PROMPT_SYNTHESIS, IMAGE_STYLES, DEFAULT_IMAGE_STYLE
from app.agents.agent_5_ads.schemas import AdsOutput
from app.db import get_agent_context, store_agent_output
from app.config import settings
from app.core.llm import get_router
from app.state import BlitzState

logger = logging.getLogger(__name__)

# OpenAI retired dall-e-3; gpt-image-1 is the current image model and returns base64.
IMAGE_MODEL = settings.image_model


async def generate_ad_image(prompt: str) -> str | None:
    """Generate a single ad image via the configured OpenAI image model.

    Args:
        prompt: Image generation prompt string.

    Returns:
        An image URL, or a `data:image/png;base64,...` URI for models that
        return base64 (gpt-image-1). None if generation fails.
    """
    try:
        response = await asyncio.wait_for(
            litellm.aimage_generation(
                model=IMAGE_MODEL,
                prompt=prompt,
                n=1,
                size=settings.image_size,
                api_key=settings.openai_api_key,
            ),
            timeout=settings.image_timeout_seconds,
        )
        item = response.data[0]
        # gpt-image-1 returns base64 only; older url-returning models still work.
        url = getattr(item, "url", None)
        if url:
            return url
        b64 = getattr(item, "b64_json", None)
        if b64:
            return f"data:image/png;base64,{b64}"
        logger.warning("Image gen returned neither url nor b64_json")
        return None
    except asyncio.TimeoutError:
        logger.warning("Image gen timed out after 120s")
        return None
    except Exception as e:
        logger.warning("Image gen failed (%s): %s", IMAGE_MODEL, e)
        return None


async def run_ads(run_id: str, feedback: str | None = None) -> AdsOutput:
    """Run the ad creative synthesis LLM call for a given run_id.

    Args:
        run_id: Pipeline run identifier — used to fetch context from ChromaDB.
        feedback: Optional feedback to guide refinement.

    Returns:
        AdsOutput with ad copies, visuals, and A/B variations.
    """
    research_raw = get_agent_context(run_id, "research_decision")
    if research_raw is None:
        logger.warning("Agent 5: no research found in ChromaDB for run_id=%s", run_id)
        research_data = "{}"
    else:
        research_data = research_raw

    profile_raw = get_agent_context(run_id, "profile")
    if profile_raw is None:
        logger.warning("Agent 5: no profile found in ChromaDB for run_id=%s", run_id)
        profile_data = "{}"
    else:
        profile_data = profile_raw

    audience_raw = get_agent_context(run_id, "audience")
    if audience_raw is None:
        logger.warning("Agent 5: no audience found in ChromaDB for run_id=%s", run_id)
        audience_data = "{}"
    else:
        audience_data = audience_raw

    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised ad creative."
        if feedback
        else ""
    )

    prompt = ADS_SYNTHESIS_PROMPT.format(
        research_data=research_data,
        profile_data=profile_data,
        audience_data=audience_data,
        feedback=feedback_instruction,
    )

    # Routed through the shared Router: retries, rate-limit backoff, and
    # failover to the fallback model are handled there, not here.
    response = await get_router().acompletion(
        model="primary",
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.ads_temperature,
    )

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    output = AdsOutput(**data)

    # Synthesize unique image prompts via a focused LLM call
    ads_for_prompts = []
    for v in output.ad_visuals:
        ads_for_prompts.append({
            "ref": f"{v.segment} + {v.platform}",
            "visual_concept": v.visual_concept,
            "color_palette": v.color_palette,
        })
    # Build a lookup from (segment, platform) -> visual_concept from ad_visuals
    visual_concept_lookup: dict[str, str] = {}
    for v in output.ad_visuals:
        visual_concept_lookup[f"{v.segment} + {v.platform}"] = v.visual_concept

    for ab in output.ab_variations:
        # Use the matching ad_visual's visual_concept; fall back to test_hypothesis
        matched_concept = visual_concept_lookup.get(ab.ad_copy_ref, ab.test_hypothesis)
        # Carry forward color_palette from the matching ad_visual too
        matched_palette = next(
            (v.color_palette for v in output.ad_visuals if f"{v.segment} + {v.platform}" == ab.ad_copy_ref),
            [],
        )
        ads_for_prompts.append({
            "ref": f"{ab.ad_copy_ref} + {ab.variant_label}",
            "visual_concept": matched_concept,
            "color_palette": matched_palette,
        })

    style_directive = IMAGE_STYLES.get(DEFAULT_IMAGE_STYLE, IMAGE_STYLES["conceptual_sketch"])

    img_prompt = IMAGE_PROMPT_SYNTHESIS.format(
        research_data=research_data,
        ads_json=json.dumps(ads_for_prompts, indent=2),
        style_directive=style_directive,
    )

    # Image prompts are a refinement on top of an already-complete AdsOutput.
    # This call used to sit outside the try below, so any failure here — a
    # provider outage, an empty balance — destroyed the entire run's ad output
    # instead of just leaving the default prompts in place.
    try:
        img_response = await get_router().acompletion(
            model="mini",
            messages=[{"role": "user", "content": img_prompt}],
            temperature=settings.image_prompt_temperature,
        )

        img_content = img_response.choices[0].message.content or "[]"
        img_content = re.sub(r"```(?:json)?\n?", "", img_content).strip().rstrip("```").strip()

        img_prompts = json.loads(img_content)
        visual_map = {f"{v.segment} + {v.platform}": i for i, v in enumerate(output.ad_visuals)}
        ab_map = {f"{ab.ad_copy_ref} + {ab.variant_label}": i for i, ab in enumerate(output.ab_variations)}
        for item in img_prompts:
            ref = item.get("ref", "")
            prompt_text = item.get("image_prompt", "")
            if ref in visual_map:
                output.ad_visuals[visual_map[ref]].image_prompt = prompt_text
            elif ref in ab_map:
                output.ab_variations[ab_map[ref]].image_prompt = prompt_text
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Image prompt synthesis failed, keeping defaults: %s", e)

    return output


async def agent_5_ads_node(state: BlitzState) -> dict:
    """Ad Creative Generator node: produces platform-specific ads with AI images.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step and ads_output.
    """
    run_id: str = state.get("run_id", "")
    feedback = state.get("ads_critic_feedback", None)

    output = await run_ads(run_id, feedback=feedback)

    store_agent_output(run_id, "ads", json.dumps(output.model_dump()))

    return {
        "current_step": 5,
        "ads_output": output.model_dump(),
    }
