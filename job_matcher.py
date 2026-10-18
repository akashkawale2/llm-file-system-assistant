"""Hybrid candidate retrieval with explicit, evidence-based hard filters."""
import argparse
import json
import math
import re
import time
from pathlib import Path
from resume_rag import ResumeRAG, SKILLS, extract_skills


def canonical_skill(value):
    for name, aliases in SKILLS.items():
        if value.strip().lower() in [name.lower(), *[x.lower() for x in aliases]]:
            return name
    raise ValueError(f'Unknown skill: {value}. Extend SKILLS to support it.')


def parse_requirements(jd, must_have=(), skill_years=None, min_years=None):
    """Parse only unambiguous constraints; structured CLI overrides are recommended."""
    required = {canonical_skill(x) for x in must_have}
    years = {canonical_skill(k): float(v) for k, v in (skill_years or {}).items()}
    for line in jd.splitlines():
        found_required = re.search(r'\bmust[- ]have\s*:\s*(.*)', line, re.I)
        if found_required:
            required.update(extract_skills(found_required.group(1)))
    for match in re.finditer(r'(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?(?:experience\s+(?:with|in)\s+)?([A-Za-z+#. ]+)', jd, re.I):
        # Only recognize a skill immediately after the number phrase.
        tail = match.group(2).strip()
        for name, aliases in SKILLS.items():
            if any(re.match(re.escape(a) + r'(?!\w)', tail, re.I) for a in aliases):
                years[name] = max(years.get(name, 0), float(match.group(1)))
                required.add(name)
    if min_years is None:
        found = re.search(r'minimum\s+(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?(?:total|professional)\s+experience', jd, re.I)
        min_years = float(found.group(1)) if found else None
    if min_years is not None and (not math.isfinite(min_years) or min_years < 0):
        raise ValueError('Minimum years must be finite and nonnegative.')
    if any(not math.isfinite(v) or v < 0 for v in years.values()):
        raise ValueError('Skill years must be finite and nonnegative.')
    return required | set(years), years, min_years


class JobMatcher:
    def __init__(self, rag=None):
        self.rag = rag if rag is not None else ResumeRAG()

    def match(self, job_description, k=10, must_have=(), skill_years=None,
              min_years=None, semantic_weight=0.7):
        if not job_description.strip() or k < 1 or not 0 <= semantic_weight <= 1:
            raise ValueError('Supply a nonempty JD, positive K, and weight between 0 and 1.')
        start = time.perf_counter()
        required, years, minimum = parse_requirements(job_description, must_have, skill_years, min_years)
        jd_skills = set(extract_skills(job_description)) | required
        count = self.rag.collection.count()
        base = {'job_description': job_description, 'top_matches': []}
        if not count:
            raise ValueError('Index is empty. Run resume_rag.py first.')
        query = {'query_embeddings': self.rag.embed([job_description]), 'n_results': count,
                 'include': ['documents', 'metadatas', 'distances']}
        if minimum is not None:
            query['where'] = {'experience_years': {'$gte': minimum}}
        hits = self.rag.collection.query(**query)
        # For this small dataset retrieve all chunks, then return K unique eligible resumes.
        # This gives keyword candidates a chance even when vector similarity is low.
        grouped = {}
        for document, metadata, distance in zip(hits['documents'][0], hits['metadatas'][0], hits['distances'][0]):
            skills = set(json.loads(metadata['skills_json']))
            experience = json.loads(metadata['skill_years_json'])
            if not required.issubset(skills) or any(experience.get(s, -1) < y for s, y in years.items()):
                continue
            path = metadata['resume_path']
            similarity = max(0.0, min(1.0, 1.0-float(distance)))
            entry = grouped.setdefault(path, {'metadata': metadata, 'evidence': [], 'similarity': 0.0})
            entry['similarity'] = max(entry['similarity'], similarity)
            entry['evidence'].append((similarity, metadata['section'], document))
        for path, entry in grouped.items():
            meta = entry['metadata']
            matched = sorted(jd_skills & set(json.loads(meta['skills_json'])))
            coverage = len(matched)/len(jd_skills) if jd_skills else 0.0
            weight = semantic_weight if jd_skills else 1.0
            score = 100*(weight*entry['similarity']+(1-weight)*coverage)
            evidence = sorted(entry['evidence'], key=lambda e: (-e[0], e[1]))[:3]
            missing = sorted(jd_skills-set(matched))
            reasoning = f"Matched sections: {', '.join(dict.fromkeys(e[1] for e in evidence))}. "
            reasoning += f"JD skill coverage: {len(matched)}/{len(jd_skills)}. "
            reasoning += 'Missing JD skills: ' + (', '.join(missing) or 'none') + '. '
            reasoning += 'All configured hard requirements passed.'
            base['top_matches'].append({'candidate_name': meta['candidate_name'], 'resume_path': path,
                'match_score': round(score, 2), 'matched_skills': matched,
                'relevant_excerpts': [e[2] for e in evidence], 'reasoning': reasoning,
                'score_components': {'semantic_similarity': round(entry['similarity'], 4),
                                     'skill_coverage': round(coverage, 4)},
                'experience_years': None if meta['experience_years'] < 0 else meta['experience_years']})
        base['top_matches'].sort(key=lambda m: (-m['match_score'], m['resume_path']))
        base['top_matches'] = base['top_matches'][:k]
        base['search_metadata'] = {'latency_ms': round((time.perf_counter()-start)*1000, 2),
            'eligible_candidates': len(grouped), 'required_skills': sorted(required),
            'required_skill_years': years, 'minimum_total_years': minimum,
            'semantic_weight': semantic_weight, 'score_is_probability': False}
        return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--jd')
    source.add_argument('--jd-file')
    parser.add_argument('--db', default='chroma_db')
    parser.add_argument('--k', type=int, default=10)
    parser.add_argument('--must-have', nargs='*', default=[])
    parser.add_argument('--skill-years', default='{}', help='JSON, e.g. {"Python": 5}')
    parser.add_argument('--min-years', type=float)
    parser.add_argument('--output', help='Optional output JSON path')
    args = parser.parse_args()
    jd = Path(args.jd_file).read_text() if args.jd_file else args.jd
    result = JobMatcher(ResumeRAG(args.db)).match(jd, args.k, args.must_have,
        json.loads(args.skill_years), args.min_years)
    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized+'\n')
    print(serialized)

if __name__ == '__main__':
    main()
