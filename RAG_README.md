# RAG Based Profile Matching — Milestone 2

This extends the LLM-Powered File System Assistant without changing its existing CLI. `resume_rag.py` directly reuses Milestone 1's `fs_tools.list_files` and `fs_tools.read_file` for TXT, PDF and DOCX input.

## Quick start (Python 3.10+)

Run commands from the repository root. On macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-rag.txt
python resume_rag.py
python job_matcher.py --jd-file data/jobs/job_01.txt --output outputs/rag_matches.json
python job_matcher.py --jd-file data/jobs/job_07.txt --skill-years '{"Python": 5}'
python evaluate.py
python -m jupyterlab notebooks/experiments.ipynb
python -m unittest discover -s tests -v
```

The first index command downloads HuggingFace `sentence-transformers/all-MiniLM-L6-v2`. Internet and sufficient free disk space are needed for dependencies and model weights. Subsequent runs reuse cached weights. The RAG pipeline requires no API key. The original assistant still uses its own API configuration.

On Windows activate `.venv\Scripts\Activate.ps1`. For JSON arguments in PowerShell, use escaping appropriate to your shell or edit the Python invocation directly. Use `--db` consistently on index, match, and evaluation if changing the default index path.

## Architecture

1. List the resume folder and load each supported file using Milestone 1 tools.
2. Identify common section headings: Summary, Skills, Experience, Education, Projects, Certifications. Preserve section boundaries; split long sections into overlapping word windows (140 words, overlap 25).
3. Extract name, skill vocabulary, explicitly stated total experience, education, and explicitly stated skill-specific years.
4. Embed chunks with normalized HuggingFace embeddings. Store text, embeddings, source paths, section labels and candidate metadata in a persistent cosine Chroma collection.
5. Embed the JD with the same model, retrieve chunk similarities, and group by source resume.
6. Enforce required skills and experience. Compute hybrid score, return up to ten unique candidates, and cite the top three matching chunks.

For this small benchmark, retrieve all chunks before grouping. Returning only ten chunks could give ten excerpts from one candidate. A production system needs an expanded vector candidate pool plus an indexed keyword candidate pool before merging and ranking.

## Search and filters

```bash
python job_matcher.py --jd "Python Django developer building PostgreSQL APIs" --k 10
python job_matcher.py --jd "Backend engineer" --must-have Python Django --min-years 5
python job_matcher.py --jd "Senior Python developer" --skill-years '{"Python": 5}'
```

Use structured flags for precise hard requirements. The lightweight parser also recognizes `Must-have: Python, Django`, `5+ years Python`, and `minimum 5 years total experience`. It is not a general natural-language constraint parser. A JD merely mentioning a skill is a soft ranking signal unless marked as required.

Unknown required skills supplied via flags are rejected; extend `SKILLS` with aliases for new terms. Unknown natural-language terms are not automatically recognized, so inspect `search_metadata` to confirm parsed constraints. Experience is never inferred from mere keyword presence. Unsupported or absent totals become unknown; missing skill-specific years fail a skill-year hard requirement.

Score: `100 * (0.7 * max_chunk_cosine + 0.3 * matched_JD_skills / all_JD_skills)`.
Cosine is clipped to [0,1]. If no JD skills are recognized, only semantic similarity is used. Score is a heuristic, not a calibrated probability. Reasoning is generated from actual matching section labels, known matched/missing skills, and filter outcomes; excerpts are retrieved source chunks. No generative LLM is needed for the supplied output contract.

Output contains the required `job_description` and `top_matches` fields. Each candidate includes `candidate_name`, `resume_path`, `match_score`, `matched_skills`, `relevant_excerpts`, and `reasoning`, plus diagnostic score components. Search metadata records requirements and measured latency.

## Dataset

`data/resumes/`: 32 fictional TXT resumes, eight disciplines, four seniority tiers, varied skills and explicit experience. `data/jobs/`: seven JDs, including senior Python. Original `resumes/` retains eight mixed PDF/DOCX/TXT examples for loader verification; use `python resume_rag.py --resumes resumes` to index those instead (this replaces the current index snapshot).

`python scripts/generate_dataset.py` deterministically regenerates the 32 resumes, JDs, manifest, and relevance labels. All names and organizations in this dataset are synthetic. The eight role groups are backend, frontend, ML, data engineering, DevOps, QA, Java backend, and data analysis.

Labels are authored from the known role groups and declared seniority, independent of retrieval output. Candidate 25 has eight total years but only three Python years; candidate 17 has five Python years. Candidate 25 must fail the senior Python requirement.

## Experiments and performance metrics

A real model run is included in `evaluation_results/RESULTS.md` with raw per-query metrics and a senior Python example. The notebook includes captured real-model outputs. Rerun on your computer to confirm your own timings.

`evaluate.py` reports candidate-level Precision@10, Recall@10, nDCG@10, reciprocal rank and warm median latency over three repetitions per JD. It compares semantic weights 1.0, 0.7 and 0.4 with identical hard constraints. Outputs go to `outputs/rag_metrics.json`. The notebook also compares chunk sizes 80/140/200, visualizes metrics, and lists false positives and missed relevant resumes.

Precision divides by 10 even if fewer results are returned. Each JD has only 1–4 relevant candidates, so low Precision@10 can coexist with perfect recall. Hard filtering can return fewer than ten candidates. Latency excludes model loading and indexing but includes JD encoding, querying, grouping, filtering, and ranking.

**Do not report test-double embeddings as semantic benchmark results.** Run the real model evaluation and notebook before submission. This synthetic template dataset is easier than real resume matching and does not establish real hiring accuracy. There is no held-out tuning split; the notebook is exploratory, not a final generalization estimate.

## Robustness and limits

- Supported text-based PDFs, DOCX, TXT use existing file-path and size validation. Scanned documents need OCR.
- A load failure is reported and stops a rebuild rather than silently skipping a candidate. Rebuilds remove stale chunks and deleted resumes. Rebuild mutation is not transactional; avoid concurrent queries/rebuilds and rerun after a write failure.
- The same embedding model is checked against collection metadata. Use a separate DB for a different model.
- Experience extraction uses explicit `Total professional experience: 5 years` / `Experience: 5 years` and `Python: 5 years` patterns. It does not infer date intervals or overlapping roles.
- Metadata rules do not handle negation, every resume layout, every skill spelling, or every qualification. Education is stored as source text, not normalized to degree equivalence.
- Very long JDs and dense word chunks may be truncated at the model token limit. A future implementation should chunk JDs and use tokenizer-aware chunk sizes.
- All skills in the recognized vocabulary contribute equally to keyword coverage; tune vocabulary and weights on separately labelled data.
- This is an educational retrieval-and-matching system, with evidence-grounded template explanations. An optional generative LLM explanation layer can be added if your instructor specifically requires it.

## Submission

Read `RAG_DEMO_SCRIPT.md`, run the commands above, inspect the real outputs, execute/save the notebook, and record a 3–4 minute screen walkthrough. Push the source branch to GitHub and submit its link with your recorded video link. Do not commit `.env`, caches, downloaded model weights, or `chroma_db/`.

## Official implementation references

- https://docs.trychroma.com/docs/collections/add-data
- https://docs.trychroma.com/docs/querying-collections/query-and-get
- https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html
