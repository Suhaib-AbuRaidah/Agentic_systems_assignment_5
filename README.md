# Campus Library MCP Toolkit

A small, self-contained assignment project with **exactly three MCP tools**. The demo catalog contains six real published books with verified authors. It is not connected to the campus library, so the catalog does not imply local availability. Saved books persist in a local SQLite reading list.

## Tool design

| Category | Tool | Input | Output | Predictable failure |
| --- | --- | --- | --- | --- |
| Data | `search_catalog` | `query: str` | `SearchResult` with matching books and count | Blank query |
| Action | `save_to_reading_list` | `book_id: str` | `SaveResult` with saved/duplicate status | Unknown ID |
| Orchestration | `find_and_save_book` | `query: str` | `FindAndSaveResult` | No match or ambiguous match |

The orchestration tool reuses the search and save operations in order. It only writes when search finds exactly one book. Duplicate saves are idempotent. The server exposes no extra MCP tools or resources.

## Requirements and setup

- Python 3.11+
- `uv` (or use `python -m venv` and `pip`)
- An OpenAI API key for model-backed agent runs. The MCP connection and local tests work without a key.

```bash
uv venv .venv
uv pip install -e '.[test]' --python .venv/bin/python
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest
```

If you use `pip` instead:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

For agent runs, create a file named `.env` in this project folder. Put your own key on one line:

```text
OPENAI_API_KEY=your-key-here
```

The client loads this file automatically. `.env` is excluded from Git; keep it private and do not share it in a screencast. You can instead set `OPENAI_API_KEY` in your shell if you prefer.

`OPENAI_MODEL` optionally overrides the default `gpt-6-luna`. Agent runs use no reasoning effort and cap each model response at 300 output tokens. `LIBRARY_DB_PATH` optionally sets the SQLite file location; the default is `data/reading_list_real_books.sqlite3`. The earlier fictional-catalog reading list remains in its old file and is not mapped to the new titles.

## Run the agent

```bash
.venv/bin/python -m library_agent.client --list-tools
.venv/bin/python -m library_agent.client --demo --trace
.venv/bin/python -m library_agent.client --trace Find Designing Data-Intensive Applications and save it
```

`--list-tools` launches the FastMCP server through the Agents SDK's stdio MCP client and prints the discovered tools without calling a model. `--demo --trace` runs four prepared requests: data lookup, direct save, orchestration, and a no-match failure. It prints the agent's MCP calls and returned tool results. The client starts and closes the server process automatically.

To run the server alone for an MCP host, use `.venv/bin/python -m library_agent.server`. It communicates over stdio, so keep stdout reserved for MCP protocol messages.

## Run the browser GUI

From this project folder:

```bash
.venv/bin/python -m library_agent.web --open
```

The local interface opens at `http://127.0.0.1:8765`. If your browser does not open automatically, visit that address yourself. Stop the server with Ctrl+C in the terminal. The page adapts the supplied UltraExplainer dashboard template with its warm editorial theme, table, and panel styling. It shows the demo catalog, saved reading list, conversation, MCP tool calls, and token use. **Focus view** keeps the live demo panels together for a screencast.

Example chips fill the message box; the API is called only when you press **Send request**. Each sent message uses the same GPT-6 Luna agent settings and real stdio MCP server as the command-line demo. The browser never receives the API key. The catalog and reading-list displays load locally without model tokens.

For a short screencast, click **Focus view**, then try the chips from left to right and press **Send request** for each one. The first prompt finds two Python books without saving; the next two save a book by ID and by title; the last prompt demonstrates a no-match error. Keep the terminal running while the browser is open. The existing `recording/campus_library_mcp_demo.mp4` shows the earlier fictional catalog, so record a new video for this version.

The book names and authors were checked against their publisher listings: [The Pragmatic Programmer](https://books.pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/), [Python Crash Course](https://nostarch.com/node/691), [Designing Data-Intensive Applications](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/titlepage01.html), [Artificial Intelligence: A Modern Approach](https://www.pearson.com/en-us/subject-catalog/p/artificial-intelligence-a-modern-approach/P200000003500/9780134610993), [Clean Code](https://www.pearson.com/en-us/subject-catalog/p/clean-code-a-handbook-of-agile-software-craftsmanship/P200000009044/9780132350884), and [Learning Python](https://www.oreilly.com/library/view/learning-python-6th/9781098171292/).

## Project files

- `src/library_agent/server.py`: FastMCP server and three tool descriptions.
- `src/library_agent/service.py`: typed result models, validation, catalog search, and SQLite persistence.
- `src/library_agent/client.py`: OpenAI Agents SDK host/client and demo CLI.
- `src/library_agent/web.py` and `web_static/`: local browser GUI, based on the supplied template.
- `tests/`: local behavior and failure tests.
- `WRITTEN_SUMMARY.md`: required article and existing-server review.
- `REFLECTION.md`: design reflection.
- `DEMO_GUIDE.md`: 5–7 minute recording outline and submission checklist.
- `scripts/record_screencast.py`: legacy capture script from the earlier version.
- `recording/campus_library_mcp_demo.mp4`: earlier recording, before the real-book catalog and light GUI.

## References

- [OpenAI Agents SDK MCP guide](https://openai.github.io/openai-agents-python/mcp/)
- [MCP Python SDK first steps](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/)
