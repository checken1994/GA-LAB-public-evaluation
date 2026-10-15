#!/usr/bin/env python3
"""Deterministic C1/C2/C3/C6 + C4-corpus coverage verifier for SCP Skills.

This verifier intentionally does NOT claim C4 behavioral PASS or C5 independent
judgment. Those require observed outputs and an external verifier respectively.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.agents' / 'skills'
CASES = ROOT / '.agents' / 'skill-evals' / 'skill_pack_cases.json'
EXPECTED = {
'scp-capability-security-review','scp-computer-use-recovery','scp-dna','scp-gateway-resilience',
'scp-learning-loop-guard','scp-reality-verifier','scp-release-evidence-gate','scp-runtime-audit',
'scp-safe-latency-optimizer','scp-skill-review','scp-startup-troubleshooter','scp-task-kernel-review',
'scp-web-orchestration-safety'}
TRIGGERS = ('use when','dùng khi','review','audit','recover','verify','govern','optimi','troubleshoot','apply')

def frontmatter(text: str):
    if not text.startswith('---\n'):
        return None
    end=text.find('\n---\n',4)
    if end < 0: return None
    fm=text[4:end]
    name=re.search(r'^name:\s*(.+)$',fm,re.M)
    desc=re.search(r'^description:\s*(.+)$',fm,re.M)
    return (name.group(1).strip() if name else '', desc.group(1).strip() if desc else '')

def main():
    failures=[]; report={}
    actual={p.parent.name for p in SKILLS.glob('*/SKILL.md')}
    if actual != EXPECTED:
        failures.append({'check':'inventory','expected':sorted(EXPECTED),'actual':sorted(actual)})
    corpus=json.loads(CASES.read_text(encoding='utf-8'))
    case_skills=set(corpus.get('skills',{}))
    if case_skills != EXPECTED:
        failures.append({'check':'c4-corpus-inventory','missing':sorted(EXPECTED-case_skills),'extra':sorted(case_skills-EXPECTED)})
    for skill in sorted(EXPECTED):
        p=SKILLS/skill/'SKILL.md'
        if not p.exists(): continue
        text=p.read_text(encoding='utf-8'); lines=text.count('\n')+1; words=len(text.split())
        fm=frontmatter(text)
        item={'lines':lines,'words':words,'frontmatter':bool(fm),'cases':len(corpus.get('skills',{}).get(skill,[]))}
        if not fm:
            failures.append({'skill':skill,'check':'C1-frontmatter'})
        else:
            name,desc=fm; item['name']=name; item['description']=desc
            if name != skill: failures.append({'skill':skill,'check':'C1-name','value':name})
            if not desc or not any(t in desc.lower() for t in TRIGGERS):
                failures.append({'skill':skill,'check':'C1-trigger-description'})
        if lines > 500: failures.append({'skill':skill,'check':'C3-lines','value':lines})
        refs=[]
        for m in re.findall(r'`([^`]+)`', text):
            if 'references/' in m: refs.append(m)
        if any(x.count('/')>1 and x.startswith('references/') for x in refs):
            failures.append({'skill':skill,'check':'C3-deep-reference','refs':refs})
        cases=corpus.get('skills',{}).get(skill,[])
        if len(cases) < 3: failures.append({'skill':skill,'check':'C4-corpus','count':len(cases)})
        for c in cases:
            if not c.get('prompt') or not c.get('must_include'):
                failures.append({'skill':skill,'check':'C4-case-shape','case':c.get('id')})
        report[skill]=item
    # Index consistency is C1/C2/C6 meta evidence.
    for index in [SKILLS/'README.md', ROOT/'.agents'/'AGENTS.md', ROOT/'.agents'/'GEMINI.md']:
        if not index.exists(): failures.append({'check':'C6-index-missing','path':str(index.relative_to(ROOT))}); continue
        txt=index.read_text(encoding='utf-8')
        missing=[s for s in EXPECTED if s not in txt]
        if missing: failures.append({'check':'C6-index-stale','path':str(index.relative_to(ROOT)),'missing':sorted(missing)})
    out={'source':'deterministic-static-verifier','skills':len(actual),'cases':sum(len(v) for v in corpus['skills'].values()),'report':report,'failures':failures,'verdict':'STATIC_READY' if not failures else 'INSUFFICIENT'}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
