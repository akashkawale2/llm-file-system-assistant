"""Measure candidate-level retrieval against independent synthetic relevance labels."""
import argparse
import json
import math
import statistics
from pathlib import Path
from job_matcher import JobMatcher
from resume_rag import ResumeRAG


def retrieval_metrics(paths, relevant, k=10):
    relevant = set(relevant)
    retrieved = paths[:k]
    flags = [int(p in relevant) for p in retrieved]
    hits = sum(flags)
    dcg = sum(hit/math.log2(i+2) for i,hit in enumerate(flags))
    ideal = sum(1/math.log2(i+2) for i in range(min(k,len(relevant))))
    return {'precision_at_10':hits/k, 'recall_at_10':hits/len(relevant) if relevant else 0,
            'ndcg_at_10':dcg/ideal if ideal else 0,
            'reciprocal_rank':next((1/(i+1) for i,x in enumerate(flags) if x),0),
            'returned':len(retrieved), 'relevant_count':len(relevant)}


def evaluate(matcher, queries, weight=0.7, repeats=3, hard_filters=True):
    if repeats < 1:
        raise ValueError('repeats must be positive')
    rows = []
    # Warm-up excludes first query startup effects from repeated latency measurements.
    matcher.match(Path(queries[0]['path']).read_text())
    for q in queries:
        jd = Path(q['path']).read_text()
        latencies=[]
        for _ in range(repeats):
            result = matcher.match(jd, semantic_weight=weight,
                must_have=q['must_have'] if hard_filters else (),
                skill_years=q['skill_years'] if hard_filters else {})
            latencies.append(result['search_metadata']['latency_ms'])
        metrics = retrieval_metrics([m['resume_path'] for m in result['top_matches']],q['relevant'])
        rows.append({'job_id':q['id'], **metrics,'median_latency_ms':statistics.median(latencies)})
    fields=['precision_at_10','recall_at_10','ndcg_at_10','reciprocal_rank','median_latency_ms']
    return {'semantic_weight':weight, 'repeats':repeats, 'queries':rows,
            'macro_average':{key:statistics.mean(r[key] for r in rows) for key in fields},
            'notes':'Synthetic, small, template-based benchmark; not evidence of real-world hiring accuracy. Latency excludes model loading and indexing. JD text constraints remain active.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='chroma_db')
    parser.add_argument('--output',default='outputs/rag_metrics.json')
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    queries=json.loads(Path('data/relevance.json').read_text())
    matcher=JobMatcher(ResumeRAG(args.db))
    result={'experiments':[evaluate(matcher,queries,w,args.repeats) for w in [1.0,0.7,0.4]]}
    path=Path(args.output)
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
