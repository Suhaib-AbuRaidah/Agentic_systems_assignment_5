"""Exercise the real stdio MCP connection without a model or API key."""

import asyncio
import os
import sqlite3
import sys

from agents.mcp import MCPServerStdio


def test_all_three_tools_over_mcp(tmp_path):
    db_path = tmp_path / "protocol-reading-list.sqlite3"

    async def exercise():
        async with MCPServerStdio(
            name="Protocol test",
            params={
                "command": sys.executable,
                "args": ["-m", "library_agent.server"],
                "env": {**os.environ, "LIBRARY_DB_PATH": str(db_path)},
            },
            client_session_timeout_seconds=30,
        ) as server:
            tools = await server.list_tools()
            assert {tool.name for tool in tools} == {
                "search_catalog", "save_to_reading_list", "find_and_save_book"
            }

            search = await server.call_tool("search_catalog", {"query": "Python"})
            assert not search.is_error
            assert "LIB-102" in str(search.structured_content or search.content)
            assert "LIB-106" in str(search.structured_content or search.content)
            assert not db_path.exists()

            saved = await server.call_tool("save_to_reading_list", {"book_id": "LIB-104"})
            assert not saved.is_error
            assert "LIB-104" in str(saved.structured_content or saved.content)

            combined = await server.call_tool("find_and_save_book", {"query": "Designing Data-Intensive Applications"})
            assert not combined.is_error
            assert "LIB-103" in str(combined.structured_content or combined.content)

            failure = await server.call_tool("find_and_save_book", {"query": "marine biology"})
            assert failure.is_error
            assert "No catalog book" in str(failure.content)

    asyncio.run(exercise())
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reading_list").fetchone()[0] == 2
