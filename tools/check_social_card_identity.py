import json, glob, os
from pathlib import Path

ROOT=Path('.')
TARGETS={4,9,84094}

def load(path):
    p=ROOT/path
    if not p.exists(): return None
    with p.open(encoding='utf-8') as f: return json.load(f)

def find_rows(obj):
    out=[]
    if isinstance(obj,list):
        rows=obj
    elif isinstance(obj,dict):
        rows=[]
        for k in ('cards','records','results','items','data'):
            if isinstance(obj.get(k),list): rows=obj[k]; break
        if not rows:
            rows=[v for v in obj.values() if isinstance(v,dict)]
    else: rows=[]
    for r in rows:
        if not isinstance(r,dict): continue
        fid=r.get('fragranticaId', r.get('fragrantica_id'))
        try: fid=int(fid)
        except: continue
        if fid in TARGETS: out.append(r)
    return out

raw=load('social-card-main-notes.json')
val=load('social-card-main-notes-validated.json')
db=load('database_complete.json')

report={
 'rule':'Identity audit only; no database writes. Social-card filename must end in exact Fragrantica ID.',
 'targets':{}
}
for fid in sorted(TARGETS):
    patterns=[
      f'fragrantica-scraper-archive/social-cards/images/*_{fid}.jpeg',
      f'fragrantica-scraper-archive/social-cards/images/*_{fid}.jpg',
      f'fragrantica-social-cards/images/*_{fid}.jpeg',
      f'fragrantica-social-cards/images/*_{fid}.jpg',
    ]
    files=[]
    for pat in patterns: files += glob.glob(pat)
    files=sorted(set(files))
    report['targets'][str(fid)]={
      'raw':find_rows(raw) if raw is not None else [],
      'validated':find_rows(val) if val is not None else [],
      'database':find_rows(db) if db is not None else [],
      'archiveFiles':files,
      'archiveBasenames':[os.path.basename(x) for x in files],
      'exactSuffixOk':all(os.path.basename(x).rsplit('_',1)[-1].split('.')[0]==str(fid) for x in files),
    }

Path('social-card-identity-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
