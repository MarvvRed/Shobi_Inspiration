import json,re,unicodedata
from pathlib import Path
from difflib import SequenceMatcher

URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
TARGETS=[Path('database_complete.json'),Path('database_v2_clean.json')]
REPORT=Path('fragrantica-v2-web-to-local-revalidation.md')

STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','fragrance'}
def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())
def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def sim(a,b):
    ta=set(toks(a));tb=set(toks(b))
    if not ta or not tb:return 0.0,0.0
    inter=len(ta&tb);cov=inter/len(ta);jac=inter/len(ta|tb)
    seq=SequenceMatcher(None,' '.join(toks(a)),' '.join(toks(b))).ratio()
    return max((cov+jac)/2,seq),cov

def parse(u):
    m=re.search(r'/perfume/([^/]+)/([^/]+?)-(\d+)\.html(?:\?.*)?$',u.strip(),re.I)
    if not m:return None
    b,n,i=m.groups();return i,b.replace('-',' '),n.replace('-',' '),u.strip()
by_id={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    p=parse(line)
    if p and p[0] not in by_id:by_id[p[0]]=p[1:]

def walk(o):
    if isinstance(o,list):
        for x in o:yield from walk(x)
    elif isinstance(o,dict):
        if 'perfumes' in o and isinstance(o['perfumes'],list):
            for p in o['perfumes']:
                if isinstance(p,dict):yield p
        elif 'code' in o or 'inspiredBy' in o:yield o

# use clean DB as canonical list of prior web rows
canon=json.loads(TARGETS[1].read_text(encoding='utf-8-sig'))
checks={}
for p in walk(canon):
    if p.get('fragranticaStatus')!='VERIFIED_WEB_V2':continue
    code=str(p.get('code') or '').strip() or '[no-code]'
    fid=str(p.get('fragranticaId') or '').strip(); name=str(p.get('inspiredBy') or '')
    u=by_id.get(fid)
    s=c=0.0
    if u:s,c=sim(name,u[0]+' '+u[1])
    ok=bool(u and (s>=0.72 or c>=0.80))
    checks[code]=(ok,fid,u,s,c,name)

stats=[]
for path in TARGETS:
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    converted=reopened=0
    for p in walk(data):
        code=str(p.get('code') or '').strip() or '[no-code]'
        if code not in checks:continue
        ok,fid,u,s,c,name=checks[code]
        if ok:
            p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2'
            p['fragranticaVerificationSource']='fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
            p['fragranticaLocalUrl']=u[2]
            converted+=1
        else:
            # do not keep web-only evidence as certified in clean-v2
            p['fragranticaStatus']='PENDING_LOCAL_CORPUS_REVIEW'
            p['fragranticaVerificationSource']=''
            reopened+=1
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stats.append((str(path),converted,reopened))

lines=['# Revalidation of prior web mappings against local perfume_urls.txt','',f'- Prior VERIFIED_WEB_V2 rows checked: **{len(checks)}**',f'- Confirmed by local corpus: **{sum(1 for v in checks.values() if v[0])}**',f'- Reopened because local corpus did not confirm strongly: **{sum(1 for v in checks.values() if not v[0])}**','','No web access is used in this pass.','']
for code,(ok,fid,u,s,c,name) in checks.items():
    if not ok:
        lines.append(f"- REOPEN `{code}` — {name} — ID {fid} — local URL: {u[2] if u else 'ABSENT'} — score {s:.4f} coverage {c:.4f}")
for p,a,b in stats:lines.append(f'- `{p}`: converted **{a}**, reopened **{b}**')
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('checked',len(checks),'confirmed',sum(1 for v in checks.values() if v[0]),'reopened',sum(1 for v in checks.values() if not v[0]))
