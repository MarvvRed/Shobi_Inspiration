#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/'database/audits/current-yellow-label-ocr-v2.json'
CAT=ROOT/'database/catalog/database_complete.json'
SITE=ROOT/'database/catalog/catalog_site.json'
OUT=ROOT/'database/audits/current-yellow-v2-exact-validation.json'

def code(x): return str(x or '').strip().upper()

def main():
    pilot=json.loads(PILOT.read_text(encoding='utf-8'))
    catalog=json.loads(CAT.read_text(encoding='utf-8-sig'))
    site=json.loads(SITE.read_text(encoding='utf-8-sig'))
    by={code(r.get('code')):r for r in catalog}
    site_by={code(r.get('code')):r for r in site}
    rows=[]
    for r in pilot.get('rows',[]):
        if r.get('result')!='EXACT_LABEL_SEQUENCE':
            continue
        c=code(r.get('code')); cat=by.get(c); s=site_by.get(c)
        reasons=[]
        if not cat: reasons.append('MISSING_CATALOG_ROW')
        else:
            if str(cat.get('fragranticaId') or '') != str(r.get('fid') or ''): reasons.append('FID_MISMATCH')
            if list(cat.get('fragranticaSocialCardNotes') or []) != list(r.get('catalog') or []): reasons.append('CATALOG_CHANGED')
            if list(r.get('observed') or []) != list(r.get('catalog') or []): reasons.append('SEQUENCE_MISMATCH')
        if not s: reasons.append('MISSING_SITE_ROW')
        elif str(s.get('validationStatus') or '').lower()!='yellow': reasons.append('NOT_CURRENTLY_YELLOW')
        label_checks=[]
        for d in r.get('details',[]):
            winner=d.get('note')
            reads=[x for x in d.get('reads',[]) if x.get('eligible') and x.get('candidate')==winner]
            exact=[x for x in reads if x.get('exact')]
            exact_crop=[x for x in exact if x.get('variant')!='locator']
            competing=[x for x in d.get('reads',[]) if x.get('eligible') and x.get('candidate') and x.get('candidate')!=winner]
            ok=bool(d.get('confident') and len(exact)>=2 and len(exact_crop)>=1 and not competing)
            label_checks.append({'note':winner,'ok':ok,'exactReads':len(exact),'exactCropReads':len(exact_crop),'competingEligibleReads':len(competing)})
        if not label_checks or not all(x['ok'] for x in label_checks): reasons.append('NOT_ALL_LABELS_STRONG_EXACT')
        status='STRONG_EXACT' if not reasons else 'REVIEW'
        rows.append({'code':c,'fid':str(r.get('fid') or ''),'status':status,'reasons':reasons,'labels':label_checks})
    counts=Counter(x['status'] for x in rows)
    payload={'source':'database/audits/current-yellow-label-ocr-v2.json','sourceMode':pilot.get('mode'),'exactCandidates':len(rows),'counts':dict(counts),'rule':'Strong exact requires current-yellow status, catalog/FID stability, exact ordered equality, and for every label >=2 eligible exact OCR reads including >=1 crop read, with zero competing eligible candidates.','rows':rows}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'exactCandidates':len(rows),'counts':dict(counts),'output':str(OUT)}))

if __name__=='__main__': main()
