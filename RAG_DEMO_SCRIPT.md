# 3–4 minute recording walkthrough

Prepare: activate your environment, install requirements, run indexing once to cache the model, execute evaluation, and run/save the notebook. Keep README, two code files, notebook, and terminal ready. Record with your own screen and voice; this file is a guide, not a video.

## 0:00–0:30 — Goal and data

“I'm extending my Milestone 1 file-system assistant into a RAG profile matcher. It uses 32 explicitly fictional resumes across eight disciplines and seven job descriptions. It returns ranked candidates with skills and source evidence.”

Show `data/resumes`, `data/jobs`, and one resume. Explain that the dataset is synthetic.

## 0:30–1:10 — Processing and vector database

Show `resume_rag.py`: reuse of `fs_tools`, section splitting, metadata, normalized embeddings, Chroma persistence.

```bash
python resume_rag.py
```

Explain that long sections are split with overlap; education and experience stay separate. Show resume and chunk counts. Mention that skill-specific years and total years are different metadata.

## 1:10–2:05 — Search and explain a result

```bash
python job_matcher.py --jd-file data/jobs/job_01.txt --output outputs/rag_matches.json
```

Show the first result in the JSON file. Explain the hybrid weighting, candidate-level grouping, matched skills, exact section excerpts, and reasoning. Point out that score is not a probability and fewer than ten candidates may pass hard filters.

## 2:05–2:45 — Demonstrate must-have years

```bash
python job_matcher.py --jd-file data/jobs/job_07.txt --skill-years '{"Python": 5}'
```

Show candidate 17's five Python years and candidate 25's eight total / three Python years. Verify candidate 25 is excluded. Do not claim exclusion based on total years alone.

## 2:45–3:35 — Evaluation and analysis

Show executed notebook weight comparison chart, chunk-size comparison and error analysis. Describe actual measured Recall@10, nDCG and latency from your run. Mention precision's fixed denominator and the small synthetic benchmark. Do not invent or pre-script metric numbers.

## 3:35–3:55 — Verification and conclusion

Show test result:

```bash
python -m unittest discover -s tests -v
```

“Known limits are scanned PDFs, rule-based metadata extraction, model truncation, and the small templated dataset. Next I would add tokenizer-aware chunking, better metadata extraction and independently reviewed evaluation data.”

Submit the GitHub branch URL and a viewable video link. Verify the video permission settings yourself.
