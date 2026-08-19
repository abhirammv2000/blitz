"""Manual smoke script: drive the real pipeline against a live URL.

This makes real API calls and costs real money. It is a debugging aid, not a
test — the automated suite lives in backend/tests/ and runs offline for free.

Usage:
    cd backend
    python test_script.py [url]
"""

import asyncio
import sys

import litellm

from app.config import settings
from app.graph import build_graph

DEFAULT_URL = "https://linear.app"


async def main(url: str) -> None:
    print(f"Running the pipeline against {url}")
    print(f"  primary={settings.primary_model}  mini={settings.mini_model}")

    graph = build_graph()
    config = {"configurable": {"thread_id": "manual-smoke"}}

    # NOTE: the state key is `company_url`, not `url`. An earlier version of this
    # script passed `url`, which the graph ignored — agent 0 then researched an
    # empty string and every downstream agent inherited the nonsense.
    initial_state = {
        "run_id": "manual-smoke",
        "company_url": url,
        "current_step": 0,
    }

    final: dict = {}
    async for chunk in graph.astream(initial_state, config=config, stream_mode="values"):
        final = chunk
        produced = [k for k in chunk if k.endswith("_output") and chunk.get(k)]
        print(f"  step {chunk.get('current_step')}: {len(produced)}/6 agents complete")

    print("\nFinished.")
    for key in (
        "research_output", "profile_output", "audience_output",
        "content_output", "sales_output", "ads_output",
    ):
        print(f"  {'OK  ' if final.get(key) else 'MISS'} {key}")


if __name__ == "__main__":
    if "-v" in sys.argv:
        litellm._turn_on_debug()
    target = next((a for a in sys.argv[1:] if not a.startswith("-")), DEFAULT_URL)
    asyncio.run(main(target))
