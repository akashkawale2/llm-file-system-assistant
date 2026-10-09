# LLM-Powered File System Assistant

A Python CLI that lets an OpenAI model choose filesystem tools to inspect fictional resumes, find keywords, and create summaries. Includes eight sample resumes across PDF, TXT, and DOCX.

## Setup (Python 3.10+)

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
```

Edit `.env` and replace `your_api_key_here` with your OpenAI API key. API access/billing is separate from a ChatGPT subscription. Never commit `.env`. The default model is `gpt-4o-mini`; set `OPENAI_MODEL` to another tool-capable model available to your API account if needed.

## Usage

Run from the project directory:

```bash
python llm_file_assistant.py
```

Try these prompts in order:

1. `Read all resumes in the resumes folder`
2. `Find resumes mentioning Python experience. Distinguish professional experience from coursework.`
3. `Create a summary file for resumes/resume_john_doe.pdf at outputs/john_summary.txt`
4. `Read outputs/john_summary.txt`

Or run a single query:

```bash
python llm_file_assistant.py --query "Find resumes mentioning Python experience"
```

`[TOOL CALL]` shows the model-selected function and arguments; `[TOOL RESULT]` shows the local execution result. Long terminal results are abbreviated, but the model receives the full tool result. The final natural-language answer follows. Type `exit` to quit.

## How function calling works

`TOOLS` defines four strict JSON function schemas. Each user query goes to the LLM with these schemas. If the response contains tool calls, Python validates the name, arguments, and paths, executes the corresponding function, and sends JSON results back with the original tool-call ID. The loop continues until the model returns a final answer, with a 15-round limit. Multiple calls in a response are executed sequentially.

Official reference: https://developers.openai.com/api/docs/guides/function-calling

## Files

| File | Purpose |
| --- | --- |
| `fs_tools.py` | Four structured file tools and path validation |
| `llm_file_assistant.py` | Schemas, dispatcher, LLM loop, interactive CLI |
| `resumes/` | Eight fictional sample resumes |
| `tests/test_project.py` | Offline document/tool checks and mocked LLM protocol |
| `DEMO_SCRIPT.md` | 2–3 minute recording plan |
| `.env.example` | API configuration template |

## Tool contracts

- `read_file(filepath) -> dict`: `success`, extracted `content`, `metadata`, optional warning; errors contain `success: false`, `error`, `message`. DOCX extraction includes paragraphs and table cells.
- `list_files(directory, extension=None) -> list`: immediate files with `name`, `filepath`, `extension`, byte `size`, UTC ISO `modified_date`. Accepts `.pdf` or `pdf`, case-insensitively. No recursion. Errors are a one-element list containing an error object; an empty directory returns `[]`.
- `write_file(filepath, content) -> dict`: atomic UTF-8 `.txt`/`.md` output and parent creation. Existing destinations are overwritten. The LLM dispatcher restricts writes to `outputs/`.
- `search_in_file(filepath, keyword) -> dict`: literal, case-insensitive matching; count and matches with extracted-text offsets, line number, and 70 characters of context on each side. An absent keyword returns zero matches; an empty keyword is invalid.

Paths resolve inside the project root (or `FS_ROOT` set before import). Parent traversal, resolved symlinks outside the root, and hidden paths are blocked. Read/write sizes are limited to 10 MiB. This is a local single-user application, not a hardened multi-user sandbox; concurrent hostile filesystem changes are out of scope.

## Tests and offline smoke check

```bash
python -m unittest discover -s tests -v
python -c "from fs_tools import search_in_file; print(search_in_file('resumes/resume_john_doe.pdf', 'Python'))"
```

Tests do not need an API key. They validate real PDF/DOCX/TXT parsing and mock the LLM response to check the tool-result protocol. A live model call must be tested separately using your key.

## Expected sample results

Python keyword matches: John, Priya, Sara, Rohan, Kabir. John, Priya, Sara, and Kabir describe professional Python use; Rohan describes only coursework. Model wording may vary.

## Limits and troubleshooting

- Image-only/scanned PDFs require OCR, which is not implemented. Empty extraction returns a warning.
- Corrupt documents, encrypted PDFs, invalid UTF-8, inaccessible files, unsupported formats, and invalid paths produce structured errors.
- DOCX headers, footers, and text boxes are outside this simple extractor's scope.
- Missing key: configure `.env`. Authentication or quota errors: check your API account and billing. Rate limit/network errors are surfaced; the SDK retries twice.
- Larger folders can exceed a model's context budget. Use narrower queries or a smaller resume set.
- Resume text is sent to the configured API. These samples are fictional; use appropriate permission before processing real resumes.

## Submission checklist

Submit the source folder (excluding `.env`, `.venv`, caches), `requirements.txt`, the sample resumes, this README, and your recorded 2–3 minute demo. The included demo script is a recording guide, not a recorded video. Review the code and explain the function-calling loop in your own words.
