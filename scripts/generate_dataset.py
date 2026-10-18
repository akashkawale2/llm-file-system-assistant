"""Reproducible fictional benchmark; no real candidate personal data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = [
 ('backend', 'Python Backend Developer', ['Python','Django','DRF','PostgreSQL','Docker','Git'],
  'Built REST APIs with authentication, relational models, database indexes, and asynchronous task queues.',
  'Developed an event booking service with transactional ticket inventory and API tests.'),
 ('frontend', 'Frontend Engineer', ['JavaScript','TypeScript','React','Git'],
  'Built accessible browser interfaces, reusable components, responsive layouts, and client state management.',
  'Implemented a dashboard with charts, search, and reusable forms.'),
 ('ml', 'Machine Learning Engineer', ['Python','Machine Learning','PyTorch','Pandas','Docker'],
  'Trained predictive models, evaluated validation sets, deployed inference services, and monitored data drift.',
  'Developed a document classification pipeline using vector representations and model evaluation.'),
 ('data', 'Data Engineer', ['Python','SQL','Spark','Airflow','ETL','AWS'],
  'Orchestrated batch data pipelines, transformed warehouse tables, and monitored data quality.',
  'Built an incremental ingestion pipeline with retries and scheduled warehouse jobs.'),
 ('devops', 'DevOps Engineer', ['Linux','AWS','Docker','Kubernetes','Terraform','Git'],
  'Automated infrastructure provisioning, container rollouts, observability, and incident recovery.',
  'Implemented automated deployments with infrastructure plans and rollback procedures.'),
 ('qa', 'QA Automation Engineer', ['Python','Selenium','Pytest','SQL','Git'],
  'Created regression suites, browser automation, API test cases, and reproducible defect reports.',
  'Built a parallel browser test suite and generated CI test reports.'),
 ('java', 'Java Backend Engineer', ['Java','Spring Boot','SQL','Docker','Redis'],
  'Designed JVM microservices, authentication, caching, and transactional persistence.',
  'Developed a payment processing service with idempotent requests and retry handling.'),
 ('analyst', 'Business Data Analyst', ['SQL','Excel','Tableau','Power BI','Pandas'],
  'Analyzed business performance, prepared executive dashboards, and validated reporting datasets.',
  'Created a sales dashboard with cohort analysis and revenue measures.'),
]
NAMES = ['Aarav Mehta','Diya Shah','Kabir Nair','Mira Rao','Ishaan Sen','Ananya Das','Rohan Iyer','Tara Bose',
 'Neel Patel','Sana Khan','Arjun Joshi','Ira Menon','Dev Sethi','Zoya Ali','Kunal Desai','Nina Roy',
 'Vivaan Jain','Aisha Kapoor','Aditya Kulkarni','Leela Thomas','Yash Malhotra','Meera Reddy','Ravi Verma','Sara Dutta',
 'Om Bhat','Rhea Singh','Ved Prasad','Alia George','Rehan Gupta','Pooja Naik','Nikhil Paul','Sia Chandra']


def main():
    folder = ROOT/'data/resumes'
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, name in enumerate(NAMES):
        group, role, skills, work, project = PROFILES[i % len(PROFILES)]
        tier = i//len(PROFILES)
        years = [0, 2, 5, 8][tier]
        # Cross-discipline experience and missing critical skills challenge naive keyword matching.
        skills = list(skills)
        if tier == 1:
            skills = skills[:-1]
        if tier == 3:
            skills += ['Python'] if 'Python' not in skills else ['AWS']
        skill_years = {s: max(0, years-(j % 3)) for j,s in enumerate(skills)}
        if group == 'backend' and tier == 3:
            skill_years['Python'] = 3  # Eight total years, only three explicitly in Python.
        experience = f'{years} years'
        statement = work if years else 'No professional employment yet. Completed academic coursework and internships; professional experience: 0 years.'
        content = f'''FICTIONAL SYNTHETIC RESUME — educational benchmark only
Name: {name}
Summary
{role}. {experience} total professional experience. Interested in reliable software and collaborative delivery.
Skills
{', '.join(skills)}
Experience
Total professional experience: {experience}
{role} at Fictional Example Organization {i+1}.
{statement}
Explicit professional skill experience:
{chr(10).join(f'{s}: {y} years' for s,y in skill_years.items())}
Education
{['B.E. Computer Engineering','B.Sc. Information Technology','M.Tech. Computer Science','B.E. Electronics Engineering'][tier]}, Example Institute, {2026-years}.
Projects
{project}
Certifications
Completed introductory software engineering and technical communication training.
'''
        filename = f'candidate_{i+1:02d}.txt'
        (folder/filename).write_text(content, encoding='utf-8')
        manifest.append({'resume_path':f'data/resumes/{filename}', 'name':name, 'role_group':group,
                         'experience_years':years, 'skills':skills, 'skill_years':skill_years})
    jobs = [
      ('backend','Python Backend Developer','Build Python and Django REST APIs with PostgreSQL, Docker and Git. Must-have: Python, Django', ['Python','Django'], None),
      ('frontend','Frontend Engineer','Build accessible React interfaces with TypeScript and JavaScript. Must-have: React, TypeScript', ['React','TypeScript'], None),
      ('ml','Machine Learning Engineer','Train Machine Learning models in Python and PyTorch, use Pandas, and deploy Docker inference services. Must-have: Python, PyTorch', ['Python','PyTorch'], None),
      ('data','Data Engineer','Build SQL warehouse ETL pipelines using Python, Spark and Airflow on AWS. Must-have: Spark, Airflow', ['Spark','Airflow'], None),
      ('devops','DevOps Engineer','Manage AWS infrastructure using Terraform, Kubernetes, Docker and Linux. Must-have: Kubernetes, Terraform', ['Kubernetes','Terraform'], None),
      ('qa','QA Automation Engineer','Automate regression testing using Python, Pytest and Selenium, validating SQL databases. Must-have: Selenium, Pytest', ['Selenium','Pytest'], None),
      ('backend','Senior Python Backend Developer','Build Python Django APIs using PostgreSQL. Requires 5+ years Python. Must-have: Python, Django', ['Python','Django'], {'Python':5}),
    ]
    queries = []
    for i,(group,title,jd,required,years) in enumerate(jobs,1):
        path = f'data/jobs/job_{i:02d}.txt'
        (ROOT/path).write_text(title+'\n'+jd+'\n')
        # Labels from known synthetic role group + stipulated seniority, not retrieved ranks.
        relevant = [m['resume_path'] for m in manifest if m['role_group']==group and
                    (not years or all(m['skill_years'].get(s,-1)>=y for s,y in years.items()))]
        queries.append({'id':f'job_{i:02d}', 'path':path, 'relevant':relevant,
                        'must_have':required, 'skill_years':years or {}})
    (ROOT/'data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'data/relevance.json').write_text(json.dumps(queries,indent=2)+'\n')
    print(f'Generated {len(manifest)} fictional resumes and {len(queries)} job descriptions.')

if __name__=='__main__':
    main()
