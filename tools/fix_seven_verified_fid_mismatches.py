#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json';SITE=ROOT/'catalog_site.json';VALID=ROOT/'social-card-main-notes-validated.json';RAW=ROOT/'social-card-main-notes.json';IMAP=ROOT/'perfume-images'/'map.js';CARDS=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images';OUT=ROOT/'seven-verified-fid-corrections.json'
FIX={
 '884-RAL':('9006','14446','https://www.fragrantica.com/perfume/Ralph-Lauren/Big-Pony-2-for-Women-14446.html'),
 '337-TIFF':('12922','53062','https://www.fragrantica.com/perfume/Tiffany/Tiffany-Co-Sheer-53062.html'),
 '548-CLI':('66133','372','https://www.fragrantica.com/perfume/Clinique/Clinique-Happy-372.html'),
 '1245-PRA':('1045','1044','https://www.fragrantica.com/perfume/Prada/Prada-Amber-Pour-Homme-Prada-Man-1044.html'),
 '1172-ISS':('79','721','https://www.fragrantica.com/perfume/Issey-Miyake/L-Eau-d-Issey-Pour-Homme-721.html'),
 '1086-CLI':('66133','373','https://www.fragrantica.com/perfume/Clinique/Clinique-Happy-373.html'),
 '1043-CAL':('14606','275','https://www.fragrantica.com/perfume/Calvin-Klein/CK-be-275.html'),
}
def code(v):return str(v or '').strip().upper()
def fetch(url,accept):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':accept,'Referer':'https://www.fragrantica.com/'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read(),r.headers.get('Content-Type','')
def get_card(c,fid):
 for url in (f'https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{fid}.jpeg',f'https://fimgs.net/mdimg/perfume-social-cards/en-social-{fid}.jpeg',f'https://fimgs.net/mdimg/perfume/social.{fid}.jpg'):
  try:data,ctype=fetch(url,'image/jpeg,image/*,*/*;q=0.8')
  except Exception:continue
  if len(data)>=5000 and data[:2]==b'\xff\xd8' and data[-2:]==b'\xff\xd9':
   p=CARDS/f'corrected_{c}_{fid}.jpeg';p.write_bytes(data);return str(p.relative_to(ROOT)),url
 return '',''
def get_image(fid):
 url=f'https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.{fid}.avif'
 try:data,ctype=fetch(url,'image/avif,image/*,*/*;q=0.8')
 except Exception:return '',url
 if len(data)>=1000 and (b'ftypavif' in data[:32] or b'ftypavis' in data[:32]):
  p=ROOT/'perfume-images'/f'{fid}.avif';p.write_bytes(data);return str(p.relative_to(ROOT)),url
 return '',url

db=json.loads(DB.read_text(encoding='utf-8-sig'));site=json.loads(SITE.read_text(encoding='utf-8-sig'));valid_list=json.loads(VALID.read_text(encoding='utf-8'));raw_list=json.loads(RAW.read_text(encoding='utf-8'));vby={code(x.get('code')):x for x in valid_list};rby={code(x.get('code')):x for x in raw_list};prefix='window.PERFUME_IMAGE_MAP=';txt=IMAP.read_text(encoding='utf-8').strip();imap=json.loads(txt[len(prefix):].rstrip(';'));changes=[]
for r,s in zip(db,site):
 c=code(r.get('code'));f=FIX.get(c)
 if not f:continue
 old,new,url=f
 if str(r.get('fragranticaId') or '')!=old:raise SystemExit(f'Unexpected FID for {c}: {r.get("fragranticaId")}')
 card,cardurl=get_card(c,new);img,imgurl=get_image(new)
 if not card:raise SystemExit(f'No exact current Social Card for corrected {c} {new}')
 # Preserve old derived evidence only if an already validated record for this exact new FID exists.
 src=vby.get(c) or {}; exact_valid=src.get('validated') is True and str(src.get('fragranticaId') or '')==new and src.get('card') and (ROOT/str(src.get('card'))).is_file()
 r['fragranticaId']=new;r['fragranticaUrl']=url;r['fragranticaVerificationSource']=url;r['identityStatus']='CONFIRMED';s['fragranticaUrl']=url
 if img:imap[c]=img
 if exact_valid:
  notes=list(src.get('mainNotes') or []);r['fragranticaSocialCardNotes']=notes;r['fragranticaSocialCardStatus']='VALIDATED_OCR'
 else:
  r['fragranticaSocialCardNotes']=[];r['fragranticaSocialCardStatus']=''
  # replace stale validation/raw entry so old-FID evidence cannot accidentally pass later
  vby[c]={'code':c,'fragranticaId':int(new),'card':card,'validated':False,'mainNotes':[],'rawSlots':[],'validatedSlots':[],'failures':[],'reasons':['PENDING_CURRENT_FID_OCR']}
  rby[c]={'code':c,'fragranticaId':int(new),'card':card,'mainNotes':[],'slots':[],'ocrConfidence':None}
 # Gender/season evidence must be rebuilt from corrected ID unless already exact elsewhere.
 r['genderStatus']='';r['seasons']=[];s['seasons']=[]
 changes.append({'code':c,'oldFid':old,'newFid':new,'url':url,'card':card,'cardSource':cardurl,'image':img,'imageSource':imgurl,'usedExistingValidatedNotes':exact_valid})
 time.sleep(.05)
# rebuild validation/raw lists preserving order
seen=set();newv=[]
for x in valid_list:
 c=code(x.get('code'));newv.append(vby.get(c,x));seen.add(c)
for c,x in vby.items():
 if c not in seen:newv.append(x)
seen=set();newr=[]
for x in raw_list:
 c=code(x.get('code'));newr.append(rby.get(c,x));seen.add(c)
for c,x in rby.items():
 if c not in seen:newr.append(x)
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');SITE.write_text(json.dumps(site,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');VALID.write_text(json.dumps(newv,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');RAW.write_text(json.dumps(newr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');IMAP.write_text(prefix+json.dumps(imap,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8');OUT.write_text(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'changed':len(changes),'rows':changes},ensure_ascii=False,indent=2))
