# GUI screencast guide (5–7 minutes)

Run `.venv/bin/python -m library_agent.web --open`, then click **Focus view** so the conversation, MCP activity, and reading list fit in the recording. The browser shows a small demo catalog of real published books; it does not claim these are available at the campus library.

1. **Introduction (45 seconds).** Explain the three tools: `search_catalog` (Data), `save_to_reading_list` (Action), and `find_and_save_book` (Orchestration). Show the full view and catalog table.
2. **Architecture (45 seconds).** Point out that the browser calls the agent host, which uses an MCP client to reach the FastMCP server over standard input and output. The server reads the demo catalog and local SQLite reading list.
3. **Live search (60 seconds).** In Focus view, click **Search Python**, then **Send request**. Show the two results, `search_catalog` in MCP activity, and the unchanged reading list.
4. **Live action (60 seconds).** Click **Save LIB-104** and send. Show `save_to_reading_list` and the new reading-list entry.
5. **Live orchestration (60 seconds).** Click **Find & save** and send. Show `find_and_save_book` and the newly saved title.
6. **Failure case (45 seconds).** Click **Try no match** and send. Explain that the orchestration tool returns an error before writing.
7. **Reflection (45 seconds).** Explain why an ambiguous search also stops before saving, show the token counts, and mention that real deployment would connect to a library catalog and add user accounts.

The old MP4 in `recording/` was produced before the real-book catalog and light GUI. Make a fresh recording for submission.
