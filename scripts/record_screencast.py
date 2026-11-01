"""Record a six-minute narrated screencast of the actual MCP agent demo.

Run under a 1280x720 Xvfb display. The script never opens or displays .env.
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "recording"
OUT.mkdir(exist_ok=True)
VIDEO = OUT / "campus_library_mcp_demo.mp4"
SILENT = OUT / "silent_capture.mp4"
LOG = OUT / "capture.log"
TRANSCRIPT = OUT / "demo_transcript.txt"

CHAPTERS = [
    {
        "seconds": 40,
        "title": "Campus Library MCP Toolkit",
        "note": "The demo catalog has real books. The reading list is stored locally.",
        "body": "C5: Agent Tools\n\nExactly three MCP tools\n\nDATA                 search_catalog\nACTION               save_to_reading_list\nORCHESTRATION        find_and_save_book\n\nFastMCP server + OpenAI Agents SDK client\nA local SQLite reading list records saved books.",
        "voice": "This is my campus library M C P toolkit for the Agent Tools assignment. It has exactly three tools: a data tool called search catalog, an action tool called save to reading list, and an orchestration tool called find and save book. The demo catalog contains six real published books, but it is not connected to campus holdings. Saved entries go into a local SQLite reading list. I will show the code, its checks, and a real agent run through the M C P server.",
    },
    {
        "seconds": 45,
        "title": "Host, client, and server",
        "note": "The agent chooses a tool; the MCP client sends the call to FastMCP.",
        "body": "USER REQUEST\n     |\n     v\nOpenAI Agents SDK agent     <- host\n     |\n     v\nMCPServerStdio              <- client connection\n     |  tools/list and tools/call\n     v\nFastMCP process             <- server\n     |\n     v\nSample catalog / SQLite reading list\n\nThe response returns along the same path.",
        "voice": "The user talks to the agent application, which is the M C P host. Inside it, the OpenAI Agents SDK creates a standard input and output client connection. That client discovers the three tool descriptions from the Fast M C P server. When the model chooses one, the client sends its name and typed arguments to the server. The server performs the operation and sends back a structured result. The client returns that result to the agent, which then answers the user.",
    },
    {
        "seconds": 55,
        "title": "Three clear tool boundaries",
        "note": "Search reads. Save writes. Find-and-save composes the two operations.",
        "body": "server.py\n\n@ mcp.tool()\nsearch_catalog(query: str) -> SearchResult\n  Read only; blank query produces a clear error.\n\n@ mcp.tool()\nsave_to_reading_list(book_id: str) -> SaveResult\n  Writes one known ID; duplicate saves do not add a row.\n\n@ mcp.tool()\nfind_and_save_book(query: str) -> FindAndSaveResult\n  Searches, requires exactly one match, then saves.\n  Zero or multiple matches cause an error before writing.",
        "voice": "The data tool accepts a search query and returns matching books without changing the reading list. The action tool takes a known book I D and saves exactly one entry. It reports duplicates instead of creating another row. The orchestration tool searches first, requires one unambiguous result, and then uses the save operation. This boundary keeps read only requests safe, makes writes explicit, and gives the agent a useful high level shortcut. All three tools declare typed inputs and outputs and describe predictable failures.",
    },
    {
        "seconds": 35,
        "title": "Tests and failure cases",
        "note": "Local tests also exercise the real stdio MCP connection without model tokens.",
        "body": "$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q\n\n.......\n7 passed\n\nCoverage includes:\n- read-only catalog search\n- blank search rejection\n- persistent save and duplicate handling\n- unknown book ID rejection\n- successful find-and-save\n- no-match and ambiguous-match rejection\n- all three tools over a real MCP connection",
        "voice": "The seven tests cover normal behavior and clear error cases. Search does not create a database file. Save persists exactly once and rejects unknown book I Ds. Find and save rejects no match or multiple matches before any write. One test starts the actual M C P server through the Agents SDK connection, discovers exactly three tools, calls each one, and verifies an error response. The tests pass without an OpenAI API call.",
    },
    {
        "seconds": 120,
        "title": "Live agent and MCP round trip",
        "note": "Running four prompts once with GPT-6 Luna. Tool calls and results appear below.",
        "body": "Starting the live agent demo...\n",
        "live": True,
        "voice": "Now I will run the agent against the M C P server. First, I ask it to search for Python without saving anything. This should use the data tool and find two books. Second, I provide a book I D and ask it to save that book, which should use the action tool. Third, I ask it to find a book by title and save it. The agent should choose the orchestration tool. Finally, I ask it to find a subject that is absent from the demo catalog. That request should return a clear no match error. On screen, each round trip shows a call from the agent through the M C P client to the server, followed by the server result and the agent's response. The client also reports the actual input and output token counts for each prompt. This confirms that the tools are being used through M C P rather than by direct Python calls. The model is GPT six Luna with reasoning set to none and a small output cap, keeping this classroom demonstration inexpensive.",
    },
    {
        "seconds": 35,
        "title": "Design challenge: ambiguity before action",
        "note": "The orchestration tool never saves when search has zero or multiple matches.",
        "body": "Example request: \"Find Python and save it\"\n\nSearch result: two matching books\nAction: none\nError: use an exact title or book ID\n\nExample request: \"Find marine biology and save it\"\n\nSearch result: zero matches\nAction: none\nError: no catalog book matches\n\nThe action remains predictable and idempotent.",
        "voice": "The main design challenge was deciding when a search result is safe to turn into a write. A vague query can match several books. If the orchestration tool silently chose one, the reading list would contain an unintended entry. It therefore checks the search count and stops before saving unless there is exactly one match. A missing book also produces a clear error. The save tool is idempotent, so repeating the same request does not add duplicate rows.",
    },
    {
        "seconds": 30,
        "title": "Reflection and submission",
        "note": "Source, written summary, and reflection are in this project folder.",
        "body": "Project files\n\nREADME.md              setup and tool design\nWRITTEN_SUMMARY.md     MCP article + Fetch server critique\nREFLECTION.md          tool boundaries and next steps\nsrc/library_agent/     FastMCP server and agent client\ntests/                 behavior and protocol tests\n\nNext steps: connect a real catalog and add user accounts.\n\nThank you.",
        "voice": "Three tools felt right for this small use case. Search and save have separate responsibilities, while the third tool provides a common two step workflow. A real deployment would replace the static demo catalog with a live library source and add authenticated reading lists. The project folder includes the setup guide, source code, tests, written summary of the assigned article and Fetch server, and a short reflection. This concludes the demonstration.",
    },
]

assert sum(chapter["seconds"] for chapter in CHAPTERS) == 360


def create_audio() -> Path:
    audio_files = []
    for index, chapter in enumerate(CHAPTERS):
        text_file = OUT / f"narration_{index + 1}.txt"
        audio_file = OUT / f"narration_{index + 1}.wav"
        text_file.write_text(chapter["voice"])
        subprocess.run(
            [
                "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
                "-i", f"flite=textfile={text_file}:voice=slt",
                "-af", "apad", "-t", str(chapter["seconds"]),
                "-ar", "22050", "-ac", "1", str(audio_file),
            ],
            check=True,
        )
        audio_files.append(audio_file)
    list_file = OUT / "audio_files.txt"
    list_file.write_text("".join(f"file '{path}'\n" for path in audio_files))
    audio = OUT / "narration.m4a"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c:a", "aac", "-b:a", "96k", str(audio)],
        check=True,
    )
    return audio


def main() -> None:
    window = tk.Tk()
    window.title("Campus Library MCP Toolkit - screencast")
    window.geometry("1280x720+0+0")
    window.attributes("-fullscreen", True)
    window.configure(bg="#101827")

    heading = tk.Label(window, text="", fg="#e8f4ff", bg="#101827", font=("DejaVu Sans", 32, "bold"), anchor="w")
    heading.pack(fill="x", padx=48, pady=(28, 8))
    note = tk.Label(window, text="", fg="#51d4c5", bg="#101827", font=("DejaVu Sans", 17), anchor="w", wraplength=1160, justify="left")
    note.pack(fill="x", padx=48, pady=(0, 18))
    body = tk.Text(window, bg="#172235", fg="#e8f4ff", insertbackground="white", font=("DejaVu Sans Mono", 17), relief="flat", wrap="word", padx=26, pady=20)
    body.pack(fill="both", expand=True, padx=48, pady=(0, 22))
    body.tag_configure("highlight", foreground="#51d4c5")
    footer = tk.Label(window, text="", fg="#aab9c9", bg="#101827", font=("DejaVu Sans", 14), anchor="w")
    footer.pack(fill="x", padx=48, pady=(0, 24))

    events: queue.Queue[str] = queue.Queue()
    state = {"demo": None, "demo_exit": None}

    def append_line(line: str) -> None:
        body.configure(state="normal")
        tag = "highlight" if line.startswith(("USER:", "AGENT:", "TOKENS:", "MCP ROUND TRIP")) else None
        body.insert("end", line, tag)
        body.see("end")
        body.configure(state="disabled")

    def read_demo(process: subprocess.Popen[str]) -> None:
        assert process.stdout is not None
        with TRANSCRIPT.open("w") as transcript:
            for line in process.stdout:
                transcript.write(line)
                transcript.flush()
                events.put(line)
        state["demo_exit"] = process.wait()
        events.put(f"\nDemo process finished with exit code {state['demo_exit']}.\n")

    def poll_events() -> None:
        while not events.empty():
            append_line(events.get_nowait())
        window.after(100, poll_events)

    def start_demo() -> None:
        environment = dict(os.environ)
        environment["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen(
            [sys.executable, "-u", "-m", "library_agent.client", "--demo", "--trace"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        state["demo"] = process
        threading.Thread(target=read_demo, args=(process,), daemon=True).start()

    def show_chapter(index: int) -> None:
        chapter = CHAPTERS[index]
        heading.configure(text=chapter["title"])
        note.configure(text=chapter["note"])
        body.configure(state="normal")
        body.delete("1.0", "end")
        body.insert("end", chapter["body"])
        body.configure(state="disabled")
        footer.configure(text=f"C5 Agent Tools  |  Chapter {index + 1} of {len(CHAPTERS)}  |  {sum(c['seconds'] for c in CHAPTERS[:index]) // 60}:{sum(c['seconds'] for c in CHAPTERS[:index]) % 60:02d} / 6:00")
        if chapter.get("live"):
            start_demo()
            window.after(25000, lambda: note.configure(text="Data lookup and direct save: the agent selects the corresponding MCP tools."))
            window.after(50000, lambda: note.configure(text="Find-and-save: the orchestration tool searches before it writes."))
            window.after(75000, lambda: note.configure(text="Failure case: a missing subject produces a clear error with no write."))
            window.after(100000, lambda: note.configure(text="The trace and token counts below come from the real model run."))
        if index + 1 < len(CHAPTERS):
            window.after(chapter["seconds"] * 1000, lambda: show_chapter(index + 1))
        else:
            window.after(chapter["seconds"] * 1000, window.quit)

    window.update()
    with LOG.open("w") as capture_log:
        capture = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-draw_mouse", "0", "-framerate", "10", "-video_size", "1280x720", "-i", os.environ["DISPLAY"], "-t", "360", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p", str(SILENT)],
            stdout=capture_log,
            stderr=subprocess.STDOUT,
        )
        show_chapter(0)
        window.after(100, poll_events)
        window.mainloop()
        if state["demo"] is not None and state["demo"].poll() is None:
            state["demo"].terminate()
        capture.wait(timeout=30)
        if capture.returncode != 0:
            raise RuntimeError(f"Video capture failed; see {LOG}")
    window.destroy()
    if state["demo_exit"] != 0:
        raise RuntimeError(f"Live agent demo failed with exit code {state['demo_exit']}")

    audio = create_audio()
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(SILENT), "-i", str(audio), "-c:v", "copy", "-c:a", "copy", "-shortest", str(VIDEO)],
        check=True,
    )
    for temporary in [SILENT, LOG, audio, OUT / "audio_files.txt", *OUT.glob("narration_*.txt"), *OUT.glob("narration_*.wav")]:
        temporary.unlink(missing_ok=True)
    print(f"Created narrated screencast: {VIDEO}")


if __name__ == "__main__":
    main()
