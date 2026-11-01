"""Guard against closing the agent's event loop between browser requests."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from library_agent.web import AgentRuntime


def test_agent_runtime_reuses_one_open_loop():
    runtime = AgentRuntime()

    async def current_loop():
        await asyncio.sleep(0)
        return asyncio.get_running_loop()

    try:
        with ThreadPoolExecutor(max_workers=1) as request_one:
            first = request_one.submit(runtime.run, current_loop()).result()
        with ThreadPoolExecutor(max_workers=1) as request_two:
            second = request_two.submit(runtime.run, current_loop()).result()
        assert first is second
        assert not first.is_closed()
    finally:
        runtime.close()

    assert first.is_closed()
