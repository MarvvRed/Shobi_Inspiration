#!/usr/bin/env python3
"""Restore missing identity provenance from prior git versions of the exact same mapping.
Requires full git history. Never invents a source.
"""
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
YES={'VERIFIED','VALIDATED','CONFIRMED','OK','MATCH_CORRETTO','MATCH CORRETTO'}

def key(r):
    return (
        str(r.get('code') or '').strip().upper(),
        str(r.get('prestashopProductId') or '').strip(),
        str(r.get('fragranticaId') or '').strip(),
        str(r.get('fragranticaUrl') or '').strip(),
    )

targets={key(r):r for r in rows if str(r.get('identityStatus') or '').strip().upper() in YES and not str(r.get('fragranticaVerificationSource') or '').strip() and all(key(r))}
remaining=set(targets)
recovered={}
commits=subprocess.check_output(['git','log','--format=%H','--','database_complete.json'],cwd=ROOT,text=True).splitlines()
# Current commit cannot help; walk newest historical snapshots first.
for sha in commits[1:250]:
    if not remaining: break
    try:
        raw=subprocess.check_output(['git','show',f'{sha}:database_complete.json'],cwd=ROOT)
        old=json.loads(raw.decode('utf-8-sig'))
    except Exception:
        continue
    for oldrow in old:
        k=key(oldrow)
        if k not in remaining: continue
        src=str(oldrow.get('fragranticaVerificationSource') or '').strip()
        if not src: continue
        recovered[k]={
            'source':src,
            'commit':sha,
            'reason':str(oldrow.get('fragranticaVerificationReason') or '').strip(),
            'matchType':str(oldrow.get('fragranticaVerificationMatchType') or '').strip(),
        }
        remaining.remove(k)

changed=[]
for k,meta in recovered.items():
    r=targets[k]
    r['fragranticaVerificationSource']=meta['source']
    if meta['reason'] and not r.get('fragranticaVerificationReason'): r['fragranticaVerificationReason']=meta['reason']
    if meta['matchType'] and not r.get('fragranticaVerificationMatchType'): r['fragranticaVerificationMatchType']=meta['matchType']
    r['fragranticaVerificationRecoveredFromCommit']=meta['commit']
    changed.append({'code':k[0],'prestashopProductId':k[1],'fragranticaId':k[2],'source':meta['source'],'commit':meta['commit']})

DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'identity-source-history-recovery.json').write_text(json.dumps({'targets':len(targets),'changed':len(changed),'unrecovered':len(remaining),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('identity_history_targets',len(targets),'recovered',len(changed),'unrecovered',len(remaining))
