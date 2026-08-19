import asyncio
import litellm
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('.env'), override=True)
litellm.set_verbose = True

from graph import build_graph

async def test():
    print("Starting...")
    g = build_graph()
    config = {"configurable": {"thread_id": "test"}}
    async for c in g.astream({'run_id': 'test', 'url': 'https://wikipedia.org'}, config=config):
        print("Got chunk:", list(c.keys()))

if __name__ == '__main__':
    asyncio.run(test())
