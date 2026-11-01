"""OpenAI Agents SDK host/client for the local library MCP server."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.model_settings import ModelSettings, Reasoning
from dotenv import load_dotenv


DEMO_PROMPTS = (
    "Search the library catalog for Python. Do not save anything.",
    "Save book LIB-104 to my reading list.",
    "Find Designing Data-Intensive Applications and save it to my reading list.",
    "Find marine biology and save it to my reading list.",
)


def build_agent(server: MCPServerStdio) -> Agent:
    """Use the same model and tool policy in the CLI and browser UI."""
    return Agent(
        name="Campus Library Assistant",
        instructions=(
            "You assist with a classroom demo catalog of real published books; do not claim these are campus holdings. "
            "Use search_catalog for read-only searches, save_to_reading_list when a user gives a book ID, "
            "and find_and_save_book when a user asks to find and save a book. "
            "Report tool errors plainly. The reading list is local to this demo."
        ),
        model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        model_settings=ModelSettings(reasoning=Reasoning(effort="none"), max_tokens=300),
        mcp_servers=[server],
    )


async def run(prompts: list[str], list_tools: bool, trace: bool) -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    async with MCPServerStdio(
        name="Campus library server",
        params={
            "command": sys.executable,
            "args": ["-m", "library_agent.server"],
            "env": dict(os.environ),
        },
        client_session_timeout_seconds=30,
    ) as server:
        tools = await server.list_tools()
        print("Connected to MCP server. Available tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        if list_tools:
            return

        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is required for agent runs. Use --list-tools to inspect the MCP connection without it.")

        agent = build_agent(server)
        for prompt in prompts:
            print(f"\nUSER: {prompt}")
            result = await Runner.run(agent, prompt, max_turns=4)
            if trace:
                for item in result.new_items:
                    if item.type in {"tool_call_item", "tool_call_output_item"}:
                        print(f"MCP ROUND TRIP [{item.type}]: {item.raw_item}")
            print(f"AGENT: {result.final_output}")
            usage = result.context_wrapper.usage
            print(f"TOKENS: {usage.input_tokens} input, {usage.output_tokens} output, {usage.total_tokens} total")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the campus library MCP agent.")
    parser.add_argument("prompt", nargs="*", help="A request for the agent; omit with --demo or --list-tools.")
    parser.add_argument("--demo", action="store_true", help="Run four prepared prompts covering all tools and a failure.")
    parser.add_argument("--list-tools", action="store_true", help="Verify the MCP connection without an API key.")
    parser.add_argument("--trace", action="store_true", help="Print tool calls and outputs from the agent run.")
    args = parser.parse_args()
    if not (args.prompt or args.demo or args.list_tools):
        parser.error("Provide a prompt, --demo, or --list-tools.")
    prompts = list(DEMO_PROMPTS) if args.demo else ([" ".join(args.prompt)] if args.prompt else [])
    asyncio.run(run(prompts, args.list_tools, args.trace))


if __name__ == "__main__":
    main()
