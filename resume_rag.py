"""Section-aware resume indexing using Milestone 1 tools and ChromaDB."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import fs_tools

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
SKILLS = {
    'Python': ['python'], 'Django': ['django'], 'FastAPI': ['fastapi'],
    'DRF': ['drf', 'django rest framework'], 'SQL': ['sql'],
    'PostgreSQL': ['postgresql', 'postgres'], 'Java': ['java'],
    'JavaScript': ['javascript'], 'TypeScript': ['typescript'],
    'React': ['react', 'react.js'], 'Node.js': ['node.js', 'nodejs'],
    'Docker': ['docker'], 'Kubernetes': ['kubernetes', 'k8s'],
    'AWS': ['aws', 'amazon web services'], 'Git': ['git'],
    'Machine Learning': ['machine learning', 'ml'],
    'PyTorch': ['pytorch'], 'TensorFlow': ['tensorflow'],
    'Pandas': ['pandas'], 'Spark': ['spark', 'pyspark'],
    'Airflow': ['airflow'], 'ETL': ['etl'], 'Tableau': ['tableau'],
    'Power BI': ['power bi'], 'Excel': ['excel'], 'Selenium': ['selenium'],
    'Pytest': ['pytest'], 'C++': ['c++'], 'C#': ['c#'],
    '.NET': ['.net', 'dotnet'], 'Redis': ['redis'], 'MongoDB': ['mongodb'],
    'Linux': ['linux'], 'Terraform': ['terraform'], 'Spring Boot': ['spring boot'],
}
HEADINGS = {
    'summary': 'Summary', 'professional summary': 'Summary', 'profile': 'Summary',
    'skills': 'Skills', 'technical skills': 'Skills',
    'experience': 'Experience', 'work experience': 'Experience',
    'professional experience': 'Experience', 'employment history': 'Experience',
    'education': 'Education', 'academic qualifications': 'Education',
    'projects': 'Projects', 'certifications': 'Certifications',
}


def contains(text, term):
    return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I))


def extract_skills(text):
    return sorted(skill for skill, aliases in SKILLS.items()
                  if any(contains(text, alias) for alias in aliases))


def sections(text):
    """Recognize standalone section headers, including Skills: inline content."""
    result, heading, lines = [], 'Profile', []
    for line in text.splitlines():
        clean = line.strip().lstrip('#').strip()
        prefix, sep, rest = clean.partition(':')
        key = prefix.lower().strip()
        if key in HEADINGS:
            if lines:
                result.append((heading, '\n'.join(lines)))
            heading, lines = HEADINGS[key], [rest.strip()] if sep and rest.strip() else []
        elif clean:
            lines.append(clean)
    if lines:
        result.append((heading, '\n'.join(lines)))
    return result


def chunk_document(text, max_words=140, overlap=25):
    # MiniLM truncates long input: keep chunks comfortably below its token limit.
    if max_words < 10 or not 0 <= overlap < max_words:
        raise ValueError('Require max_words >= 10 and 0 <= overlap < max_words.')
    chunks = []
    for heading, content in sections(text):
        words = content.split()
        for start in range(0, len(words), max_words-overlap):
            chunks.append({'section': heading, 'text': heading + ': ' + ' '.join(words[start:start+max_words])})
            if start+max_words >= len(words):
                break
    return chunks


def extract_metadata(text, path):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    named = re.search(r'^Name\s*:\s*(.+)$', text, re.M | re.I)
    name = named.group(1).strip() if named else next(
        (x for x in lines if 'fictional' not in x.lower() and 'synthetic' not in x.lower()), Path(path).stem)
    # Conservative: only explicitly reported professional totals, never add overlapping dates.
    total = re.search(r'(?:total\s+)?(?:professional\s+)?experience\s*:\s*(\d+(?:\.\d+)?)\s*years?', text, re.I)
    skill_years = {}
    for skill, aliases in SKILLS.items():
        for alias in aliases:
            pattern = r'(?<!\w)' + re.escape(alias) + r'(?!\w)\s*:\s*(\d+(?:\.\d+)?)\s*years?'
            found = re.search(pattern, text, re.I)
            if found:
                skill_years[skill] = float(found.group(1))
                break
    education = '\n'.join(content for heading, content in sections(text) if heading == 'Education')
    return {'candidate_name': name, 'resume_path': path,
            'skills_json': json.dumps(extract_skills(text)),
            'experience_years': float(total.group(1)) if total else -1.0,
            'skill_years_json': json.dumps(skill_years), 'education': education or 'Unknown'}


class ResumeRAG:
    def __init__(self, db_path='chroma_db', model=MODEL, embedder=None, collection=None):
        self.model_name = model
        if embedder is None:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(model)
        self.embedder = embedder
        if collection is None:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(db_path))
            collection = self.client.get_or_create_collection(
                name='resume_chunks', metadata={'hnsw:space': 'cosine', 'embedding_model': model},
                embedding_function=None)
        self.collection = collection
        stored = (collection.metadata or {}).get('embedding_model')
        if stored and stored != model:
            raise ValueError('Embedding model differs from index; use a new database directory.')

    def embed(self, texts):
        return self.embedder.encode(texts, normalize_embeddings=True).tolist()

    def index_directory(self, directory='data/resumes', max_words=140, overlap=25):
        files = fs_tools.list_files(directory)
        if files and files[0].get('success') is False:
            raise ValueError(files[0]['message'])
        prepared, errors = [], []
        for item in files:
            if item['extension'] not in {'.txt', '.pdf', '.docx'}:
                continue
            loaded = fs_tools.read_file(item['filepath'])
            if not loaded['success'] or not loaded.get('content', '').strip():
                errors.append({'path': item['filepath'], 'error': loaded.get('message', 'No text extracted; OCR may be needed.')})
                continue
            text = loaded['content']
            metadata = extract_metadata(text, item['filepath'])
            chunks = chunk_document(text, max_words, overlap)
            prepared.append((item['filepath'], metadata, chunks))
        # Do not silently publish an incomplete rebuild. Existing index stays intact on read errors.
        if errors:
            raise ValueError(json.dumps({'indexing_errors': errors}))
        if not prepared:
            raise ValueError('No supported, nonempty resumes found; index unchanged.')
        docs, metas, ids = [], [], []
        for path, metadata, chunks in prepared:
            for i, chunk in enumerate(chunks):
                docs.append(chunk['text'])
                metas.append({**metadata, 'section': chunk['section']})
                ids.append(hashlib.sha256(f'{path}:{i}'.encode()).hexdigest())
        embeddings = self.embed(docs)  # Compute before replacing the previous snapshot.
        old = self.collection.get(include=[])['ids']
        if old:
            self.collection.delete(ids=old)
        for start in range(0, len(ids), 128):
            self.collection.add(ids=ids[start:start+128], documents=docs[start:start+128],
                                metadatas=metas[start:start+128], embeddings=embeddings[start:start+128])
        return {'resumes': len(prepared), 'chunks': len(ids), 'model': self.model_name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resumes', default='data/resumes')
    parser.add_argument('--db', default='chroma_db')
    args = parser.parse_args()
    print(json.dumps(ResumeRAG(args.db).index_directory(args.resumes), indent=2))

if __name__ == '__main__':
    main()
