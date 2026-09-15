#!/usr/bin/env python3
"""Recover missing identity provenance only from exact VERIFIED/PASS audit rows."""
import csv, json, re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'
AUDIT=ROOT/'database/audits/fragrantica-v2-identity-audit.csv'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))

def code(v): return str(v or '').strip().upper()
def url_id(url):
    s=str(url or '').strip()
    for p in (r'-(\d+)\.html(?:$|[?#])',r'/p/(\d+)(?:/?$|[?#])'):
        m=re.search(p,s,re.I)
        if m:return m.group(1)
    return ''

by_code=defaultdict(list)
with AUDIT.open(encoding='utf-8-sig',newline='') as f:
    for a in csv.DictReader(f): by_code[code(a.get('shobi_code'))].append(a)

changed=[]
for r in rows:
    if str(r.get('fragranticaVerificationSource') or '').strip(): continue
    if code(r.get('identityStatus')) not in {'CONFIRMED','VERIFIED','VALIDATED','OK'}: continue
    c=code(r.get('code')); fid=str(r.get('fragranticaId') or '').strip(); furl=str(r.get('fragranticaUrl') or '').strip()
    pid=str(r.get('prestashopProductId') or '').strip()
    if not (c and fid and furl and url_id(furl)==fid and pid): continue
    matches=[]
    for a in by_code.get(c,[]):
        if code(a.get('classification'))!='VERIFIED': continue
        if code(a.get('identity_gate'))!='PASS': continue
        if str(a.get('prestashop_product_id') or '').strip()!=pid: continue
        if str(a.get('fragrantica_id') or '').strip()!=fid: continue
        au=str(a.get('fragrantica_url') or '').strip()
        if not au or url_id(au)!=fid: continue
        matches.append(a)
    if len(matches)!=1: continue
    a=matches[0]
    r['fragranticaVerificationSource']='database/audits/fragrantica-v2-identity-audit.csv'
    r['fragranticaVerificationReason']=str(a.get('reason') or '').strip()
    r['fragranticaVerificationMatchType']=str(a.get('match_type') or '').strip()
    r['fragranticaVerificationAuditUrl']=str(a.get('fragrantica_url') or '').strip()
    changed.append({'code':c,'prestashopProductId':pid,'fragranticaId':fid,'reason':r['fragranticaVerificationReason']})

DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'database/audits/identity-source-audit-fixes.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('identity_sources_fixed',len(changed))
