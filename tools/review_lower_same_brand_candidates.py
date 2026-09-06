import csv,re,unicodedata
from pathlib import Path

MATCH=Path('fragrantica-v2-local-url-match.csv')
OUT=Path('fragrantica-v2-lower-same-brand-review.csv')
REPORT=Path('fragrantica-v2-lower-same-brand-review.md')
STOP={'eau','de','parfum','perfume','toilette','edp','edt','for','men','women','man','woman','pour','homme','femme','the','by','and','limited','edition','cologne','notes','note'}

def norm(v):
    s=unicodedata.normalize('NFKD',str(v or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
def tokens(v): return [x for x in norm(v).split() if x not in STOP and len(x)>1]
def brand_match(a,b):
    a,b=norm(a),norm(b)
    return bool(a and b and (a==b or a in b or b in a))

def stats(q,name):
    qt=set(tokens(q)); nt=set(tokens(name))
    if not qt or not nt:return (0.0,0.0,0)
    inter=len(qt&nt)
    return (inter/len(qt),inter/len(nt),inter)

with MATCH.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
out=[]
for r in rows:
    if r.get('classification') not in {'WEAK_REVIEW','NO_CANDIDATE','GOOD_REVIEW'}: continue
    hint=r.get('inferred_brand','').strip()
    if not hint: continue
    q=r.get('match_name') or r.get('shobi_name') or ''
    c1_name=r.get('cand1_name',''); c1_brand=r.get('cand1_brand','')
    c1_rec,c1_prec,_=stats(q,c1_name)
    best=None
    for i in range(2,6):
        cid=r.get(f'cand{i}_id','').strip(); name=r.get(f'cand{i}_name',''); brand=r.get(f'cand{i}_brand','')
        if not cid or not brand_match(hint,brand): continue
        rec,prec,inter=stats(q,name)
        # Surface lower candidates when they preserve substantially more of the
        # Shobi identity words than cand1, or preserve all distinctive words.
        qualifies=(rec>=0.75 and rec>=c1_rec+0.20) or (rec>=0.99 and prec>=0.40 and c1_rec<0.99)
        if not qualifies: continue
        score=(rec,prec,inter,-i)
        if best is None or score>best[0]: best=(score,i,cid,brand,name,r.get(f'cand{i}_url',''),rec,prec)
    if not best: continue
    _,i,cid,brand,name,url,rec,prec=best
    out.append({
      'shobi_code':r.get('shobi_code',''),'shobi_name':r.get('shobi_name',''),'inferred_brand':hint,
      'old_classification':r.get('classification',''),'cand1_id':r.get('cand1_id',''),'cand1_brand':c1_brand,
      'cand1_name':c1_name,'cand1_recall':f'{c1_rec:.4f}','lower_rank':i,'lower_id':cid,
      'lower_brand':brand,'lower_name':name,'lower_recall':f'{rec:.4f}','lower_precision':f'{prec:.4f}','lower_url':url,
    })
out.sort(key=lambda x:(float(x['lower_recall']),float(x['lower_precision']),-int(x['lower_rank'])),reverse=True)
fields=list(out[0].keys()) if out else ['shobi_code']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
lines=['# Lower same-brand candidate review','',f'- Surfaced rows: **{len(out)}**','',
       'Review-only. Uses only the already generated local-corpus candidate table; promotes nothing.','',
       '## Candidates','']
for x in out:
    lines.append(f"- `{x['shobi_code']}` — {x['shobi_name']} — cand1 `{x['cand1_name']}` (recall {x['cand1_recall']}) -> cand{x['lower_rank']} **{x['lower_brand']} / {x['lower_name']}** — ID {x['lower_id']} (recall {x['lower_recall']}, precision {x['lower_precision']})")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('surfaced',len(out))
