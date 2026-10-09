# 2–3 minute demo recording guide

Before recording: install dependencies, configure `.env`, run the tests, and verify one live query. Hide the API key. Use macOS Screenshot (Cmd+Shift+5) or another screen recorder to record terminal and editor.

**0:00–0:20 — Introduction**
"This is my LLM-powered filesystem assistant. It exposes four Python tools through structured function schemas and works with PDF, TXT, and DOCX resumes."
Show the source files and eight resumes.

**0:20–0:45 — Explain the tools**
Show `fs_tools.py`: reading and metadata, directory filtering, atomic writing, and case-insensitive search. Briefly show `TOOLS` in the assistant module.

**0:45–1:15 — Read resumes**
Run `python llm_file_assistant.py`.
Enter: `Read all resumes in the resumes folder`.
Point out `list_files` followed by `read_file` calls and their results.

**1:15–1:50 — Search**
Enter: `Find resumes mentioning Python experience. Distinguish professional experience from coursework.`
Point out `search_in_file` calls. Explain that Rohan mentions beginner Python without professional experience.

**1:50–2:20 — Create a summary**
Enter: `Create a summary file for resumes/resume_john_doe.pdf at outputs/john_summary.txt`.
Show the source read and `write_file` call. Enter `Read outputs/john_summary.txt` to verify the saved output.

**2:20–2:45 — Errors and architecture**
Enter: `Read resumes/missing.pdf` and show the graceful error.
"The model selects a function; Python validates and executes it, then returns the result to the model. The loop stops when the model produces its final answer."

Keep natural model latency in mind. Rehearse once and trim idle waiting if necessary; keep actual tool-call evidence visible. Export the recording and submit it with the project. Do not describe offline mocks as live LLM calls.
