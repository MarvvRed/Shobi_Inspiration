#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'; SITE=ROOT/'database/catalog/catalog_site.json'; VALID=ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json'; REPORT=ROOT/'database/audits/current-fid-card-multipass-validation.json'; OUT=ROOT/'database/audits/current-fid-multipass-applied.json'
def code(v): return str(v or '').strip().upper()
def card_matches(card,c,fid):
    p=Path(str(card or ''))
    return p.name.endswith(f'_{c}_{fid}.jpeg') and (ROOT/p).is_file()
db=json.loads(DB.read_text(encoding='utf-8-sig')); site=json.loads(SITE.read_text(encoding='utf-8-sig')); valid=json.loads(VALID.read_text(encoding='utf-8')); rep=json.loads(REPORT.read_text(encoding='utf-8'))
bydb={code(x.get('code')):x for x in db}; bysite={code(x.get('code')):x for x in site}; byv={code(x.get('code')):x for x in valid}
applied=[]; skipped=[]
for r in rep.get('rows',[]):
    c=code(r.get('code')); fid=str(r.get('fid') or ''); card=str(r.get('card') or ''); notes=list(r.get('notes') or []); slots=list(r.get('slots') or [])
    d=bydb.get(c); s=bysite.get(c)
    reason=''
    if not d or not s: reason='missing_current_row'
    elif str(s.get('validationStatus') or '').lower()!='yellow': reason='not_yellow_anymore'
    elif (s.get('validationChecks') or {}).get('socialCard',False): reason='social_card_already_valid'
    elif str(d.get('fragranticaId') or '')!=fid: reason='fid_changed'
    elif not card_matches(card,c,fid): reason='card_missing_or_name_mismatch'
    elif not notes or len(notes)!=len(slots): reason='invalid_accepted_payload'
    if reason:
        skipped.append({'code':c,'fid':fid,'reason':reason}); continue
    d['fragranticaSocialCardNotes']=notes
    d['fragranticaSocialCardStatus']='VALIDATED_OCR'
    byv[c]={
      'code':c,'fragranticaId':int(fid) if fid.isdigit() else fid,'card':card,'validated':True,'mainNotes':notes,
      'rawSlots':[{'slot':int(sl),'name':n,'ocrConfidence':None} for sl,n in zip(slots,notes)],
      'validatedSlots':[{'slot':int(sl),'name':n,'raw':'CURRENT_FID_MULTIPASS_OCR','matchScore':None,'margin':None} for sl,n in zip(slots,notes)],
      'failures':[],'reasons':[],'validationMethod':'CURRENT_FID_MULTIPASS_OCR'
    }
    applied.append({'code':c,'fid':fid,'card':card,'notes':notes,'slots':slots})
seen=set(); rebuilt=[]
for x in valid:
    c=code(x.get('code')); rebuilt.append(byv.get(c,x)); seen.add(c)
for c,x in byv.items():
    if c not in seen: rebuilt.append(x)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
VALID.write_text(json.dumps(rebuilt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
OUT.write_text(json.dumps({'applied':len(applied),'skipped':len(skipped),'rows':applied,'skippedRows':skipped},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'applied':len(applied),'skipped':len(skipped),'skipReasons':{k:sum(1 for x in skipped if x['reason']==k) for k in sorted({x['reason'] for x in skipped})}},ensure_ascii=False))
