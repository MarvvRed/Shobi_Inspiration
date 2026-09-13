#!/usr/bin/env python3
from __future__ import annotations
import json,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'catalog_site.json').read_text(encoding='utf-8-sig'))
OUTDIR=ROOT/'fragrantica-scraper-archive'/'social-cards'/'images';OUT=ROOT/'current-fid-card-fetch-report.json'
URLS=(
 'https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{fid}.jpeg',
 'https://fimgs.net/mdimg/perfume-social-cards/en-social-{fid}.jpeg',
 'https://fimgs.net/mdimg/perfume/social.{fid}.jpg',
)
HEAD={'User-Agent':'Mozilla/5.0 (compatible; ShobiExactCardRecovery/1.0)','Accept':'image/jpeg,image/*,*/*;q=0.8','Referer':'https://www.fragrantica.com/'}
def code(v):return str(v or '').strip().upper()
def valid_jpeg(data):return len(data)>=5000 and data[:2]==b'\xff\xd8' and data[-2:]==b'\xff\xd9'
def fetch(url):
 req=urllib.request.Request(url,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=25) as r:data=r.read();ctype=r.headers.get('Content-Type','')
  return ('OK',data,ctype) if valid_jpeg(data) else ('INVALID',None,ctype)
 except urllib.error.HTTPError as e:return (f'HTTP_{e.code}',None,'')
 except Exception as e:return (type(e).__name__,None,str(e))
rows=[]
for db,s in zip(DB,SITE):
 if str(s.get('validationStatus') or '').lower()!='yellow':continue
 checks=s.get('validationChecks') or {}
 if checks.get('socialCard',False):continue
 fid=str(db.get('fragranticaId') or '').strip();c=code(db.get('code'))
 if not fid.isdigit():continue
 target=OUTDIR/f'current_{c}_{fid}.jpeg'
 if target.is_file() and target.stat().st_size>=5000:
  rows.append({'code':c,'fid':fid,'status':'EXISTS','card':str(target.relative_to(ROOT)),'source':''});continue
 attempts=[];saved=False
 for tpl in URLS:
  url=tpl.format(fid=fid);st,data,detail=fetch(url);attempts.append({'url':url,'status':st,'detail':detail})
  if data is not None:
   target.write_bytes(data);rows.append({'code':c,'fid':fid,'status':'RECOVERED','card':str(target.relative_to(ROOT)),'source':url,'attempts':attempts});saved=True;break
 if not saved:rows.append({'code':c,'fid':fid,'status':'MISSING','card':'','source':'','attempts':attempts})
 time.sleep(.04)
out={'targets':len(rows),'recovered':sum(r['status'] in {'RECOVERED','EXISTS'} for r in rows),'missing':sum(r['status']=='MISSING' for r in rows),'rows':rows}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:out[k] for k in ('targets','recovered','missing')},indent=2))
