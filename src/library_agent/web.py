"""Local browser interface for the campus library MCP agent."""

import argparse
import asyncio
import json
import os
import sqlite3
import threading
import webbrowser
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from agents import Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

from .catalog import CATALOG
from .client import build_agent
from .service import LibraryService


ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).with_name("web_static")
CHAT_LOCK = threading.Lock()


def load_config() -> None:
    load_dotenv(ROOT / ".env", override=False)


@lru_cache(maxsize=1)
def page_html() -> bytes:
    """Keep the supplied dashboard's theme and runtime, replacing its sample data."""
    base = (STATIC / "base.html").read_text()
    body = (STATIC / "body.html").read_text()
    start = base.index('<div class="ux-wrap">')
    end = base.rindex("\n<script>")
    page = base[:start] + body + base[end:]
    page = page.replace("<title>Gateway p99 — last 24h — UltraExplainer</title>", "<title>Library Agent · MCP Workspace</title>")
    page = page.replace("</head>", '<link rel="stylesheet" href="/app.css"></head>', 1)
    page = page.replace("</body>", '<script src="/app.js" defer></script></body>', 1)
    return page.encode("utf-8")


def saved_book_ids() -> list[str]:
    path = LibraryService().db_path
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path) as connection:
            return [row[0] for row in connection.execute("SELECT book_id FROM reading_list ORDER BY saved_at, book_id")]
    except sqlite3.OperationalError:
        return []


def state_data() -> dict:
    load_config()
    return {
        "catalog": [book.model_dump() for book in CATALOG],
        "saved_ids": saved_book_ids(),
        "model": os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        "key_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


def parse_tool_output(raw: object) -> object:
    if isinstance(raw, dict):
        output = raw.get("output")
        if isinstance(output, list):
            text = "\n".join(part.get("text", "") for part in output if isinstance(part, dict))
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return output
    return str(raw)


async def run_agent(message: str) -> dict:
    load_config()
    async with MCPServerStdio(
        name="Campus library server",
        params={"command": os.sys.executable, "args": ["-m", "library_agent.server"], "env": dict(os.environ)},
        client_session_timeout_seconds=30,
    ) as server:
        result = await Runner.run(build_agent(server), message, max_turns=4)
    calls: list[dict] = []
    call_by_id: dict[str, dict] = {}
    for item in result.new_items:
        if item.type == "tool_call_item":
            raw = item.raw_item
            try:
                arguments = json.loads(raw.arguments)
            except (json.JSONDecodeError, AttributeError):
                arguments = {}
            call = {"tool": raw.name, "arguments": arguments, "result": None, "error": False}
            calls.append(call)
            call_by_id[raw.call_id] = call
        elif item.type == "tool_call_output_item" and isinstance(item.raw_item, dict):
            raw = item.raw_item
            call = call_by_id.get(raw.get("call_id"))
            if call is not None:
                call["result"] = parse_tool_output(raw)
                call["error"] = isinstance(call["result"], str) and call["result"].startswith("Error calling tool")
    usage = result.context_wrapper.usage
    return {
        "answer": str(result.final_output or ""),
        "calls": calls,
        "usage": {"input": usage.input_tokens, "output": usage.output_tokens, "total": usage.total_tokens},
    }


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status: int, data: dict) -> None:
        self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self.send_bytes(200, page_html(), "text/html; charset=utf-8")
        elif path == "/app.css":
            self.send_bytes(200, (STATIC / "app.css").read_bytes(), "text/css; charset=utf-8")
        elif path == "/app.js":
            self.send_bytes(200, (STATIC / "app.js").read_bytes(), "text/javascript; charset=utf-8")
        elif path == "/api/state":
            self.send_json(200, state_data())
        elif path == "/favicon.ico":
            self.send_bytes(204, b"", "image/x-icon")
        else:
            self.send_json(404, {"error": "Page not found."})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/chat":
            self.send_json(404, {"error": "Page not found."})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
            self.send_json(415, {"error": "Send JSON with a message field."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 1 <= length <= 4096:
            self.send_json(413, {"error": "Request is too large or empty."})
            return
        try:
            data = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Invalid JSON request."})
            return
        message = data.get("message") if isinstance(data, dict) else None
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 500:
            self.send_json(400, {"error": "Message must contain 1 to 500 characters."})
            return
        load_config()
        if not os.getenv("OPENAI_API_KEY"):
            self.send_json(503, {"error": "Set OPENAI_API_KEY in .env before sending requests."})
            return
        if not CHAT_LOCK.acquire(blocking=False):
            self.send_json(429, {"error": "The agent is finishing another request. Try again shortly."})
            return
        try:
            self.send_json(200, asyncio.run(run_agent(message.strip())))
        except Exception as error:
            print(f"Agent request failed: {type(error).__name__}", file=os.sys.stderr, flush=True)
            self.send_json(502, {"error": "The agent request failed. Check the API key and network, then try again."})
        finally:
            CHAT_LOCK.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local browser interface for the library agent.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the interface in your default browser.")
    args = parser.parse_args()
    load_config()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Library Agent is ready at {url}", flush=True)
    if args.open:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Library Agent.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
