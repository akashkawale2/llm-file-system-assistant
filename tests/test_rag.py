"""Offline logic checks; real Chroma integration uses a deterministic test embedder."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import fs_tools
from resume_rag import chunk_document, extract_metadata, extract_skills, ResumeRAG
from job_matcher import JobMatcher, parse_requirements
from evaluate import retrieval_metrics

class TestEmbedder:
    # Test double only. Never use for benchmark measurements or semantic claims.
    def encode(self, texts, normalize_embeddings=True):
        vectors=[]
        for text in texts:
            v=np.zeros(64)
            for word in text.lower().split():
                v[int(hashlib.sha256(word.encode()).hexdigest(),16)%64]+=1
            vectors.append(v/(np.linalg.norm(v) or 1))
        return np.array(vectors)

class ExtractionTests(unittest.TestCase):
    def test_boundaries_and_aliases(self):
        self.assertEqual(extract_skills('JavaScript C++ C# postgres Django REST Framework'),
                         ['C#','C++','DRF','Django','JavaScript','PostgreSQL'])
        self.assertNotIn('Java',extract_skills('JavaScript'))

    def test_sections_and_overlap(self):
        text='Name: Example\nEducation\nB.E.\nExperience\n'+' '.join(f'w{i}' for i in range(33))
        chunks=chunk_document(text,20,5)
        self.assertEqual([c['section'] for c in chunks],['Profile','Education','Experience','Experience'])
        self.assertIn('w15',chunks[2]['text'])
        self.assertIn('w15',chunks[3]['text'])
        self.assertNotIn('B.E.',chunks[2]['text'])
        with self.assertRaises(ValueError): chunk_document(text,20,20)

    def test_unknown_experience_and_specific_years(self):
        m=extract_metadata('Name: A\nSkills\nPython\nExperience\nTotal professional experience: 8 years\nPython: 3 years','x.txt')
        self.assertEqual(m['experience_years'],8)
        self.assertEqual(json.loads(m['skill_years_json'])['Python'],3)
        self.assertEqual(extract_metadata('Name: B\nPython developer','b.txt')['experience_years'],-1)
        self.assertEqual(parse_requirements('Requires 5+ years Python.')[1],{'Python':5})
        with self.assertRaises(ValueError): parse_requirements('JD',skill_years={'Python':float('nan')})

    def test_metrics(self):
        metrics=retrieval_metrics(['b','a'],['a','c'])
        self.assertEqual(metrics['precision_at_10'],.1)
        self.assertEqual(metrics['recall_at_10'],.5)
        self.assertEqual(metrics['reciprocal_rank'],.5)

class IntegrationTests(unittest.TestCase):
    def test_real_chroma_rebuild_and_hard_filter(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as db:
            folder=Path(root,'resumes');folder.mkdir()
            for name,total,python in [('A',8,3),('B',5,5),('C',1,None)]:
                (folder/f'{name}.txt').write_text(f'Name: {name}\nSkills\nPython, Django\nExperience\nTotal professional experience: {total} years\n'+(f'Python: {python} years\n' if python is not None else '')+'Education\nB.E.')
            with patch.object(fs_tools,'ROOT',Path(root).resolve()):
                rag=ResumeRAG(db,model='test-only',embedder=TestEmbedder())
                self.assertEqual(rag.index_directory('resumes')['resumes'],3)
                matcher=JobMatcher(rag)
                result=matcher.match('Must-have: Python, Django\nRequires 5+ years Python.')
                self.assertEqual([m['candidate_name'] for m in result['top_matches']],['B'])
                self.assertTrue(result['top_matches'][0]['relevant_excerpts'])
                self.assertEqual(len(matcher.match('Python Django')['top_matches']),3)
                self.assertEqual(matcher.match('Java',must_have=['Java'])['top_matches'],[])
                self.assertEqual(len(matcher.match('Python',min_years=5)['top_matches']),2)
                count=rag.collection.count()
                rag.index_directory('resumes')
                self.assertEqual(rag.collection.count(),count)
                (folder/'bad.txt').write_text('')
                with self.assertRaises(ValueError):rag.index_directory('resumes')
                self.assertEqual(rag.collection.count(),count)
                (folder/'bad.txt').unlink();(folder/'B.txt').unlink()
                rag.index_directory('resumes')
                self.assertEqual(matcher.match('5+ years Python')['top_matches'],[])
                with self.assertRaises(ValueError):matcher.match('')
                with self.assertRaises(ValueError):matcher.match('Python',k=0)

if __name__=='__main__':unittest.main()
