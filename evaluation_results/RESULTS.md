# Measured benchmark results

Run date: 2026-10-18. Dataset: 32 synthetic resumes, 7 synthetic JDs, 224 chunks. Model: sentence-transformers/all-MiniLM-L6-v2. ChromaDB 1.5.9. Python 3.12.14.

| Semantic weight | Precision@10 | Recall@10 | nDCG@10 | Mean of per-JD median latency (ms) |
| --- | --- | --- | --- | --- |
| 1.0 | 0.357 | 1.000 | 1.000 | 129.22 |
| 0.7 | 0.357 | 1.000 | 1.000 | 30.26 |
| 0.4 | 0.357 | 1.000 | 1.000 | 37.84 |

All modes use the same hard filters. These filters leave the relevant role groups almost perfectly separated; this easy synthetic benchmark cannot establish an advantage for hybrid ranking. Latency varies with warm-up and runtime scheduling; the fixed mode order can introduce caching/order effects. Do not interpret these differences as a controlled speed comparison.

Precision@10 uses a fixed denominator of ten; each query has at most four relevant resumes. Retrieval recall is perfect here, not evidence of real-world hiring accuracy.

The senior Python query returned only Vivaan Jain (candidate 17), with an illustrative score of 78.29. Candidate 25 was excluded despite eight total years because only three Python years are declared.

See metrics.json for per-query values and senior_python_match.json for source evidence. The notebook contains a separate measured run and chunk-size experiments.
