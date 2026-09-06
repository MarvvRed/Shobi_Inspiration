import json,re
from pathlib import Path
DB=Path('database_complete.json')
data=json.loads(DB.read_text(encoding='utf-8'))
# Verified from current Shobi pages / residual audit.
REMOVE_EMPTY_URL_CODES={'2313-DRC','1644-DRC'}
ASSIGN_EMPTY_URL_CODES={'2282-DRC','2133-FRE'}
# 2514-DRC: keep the live Prestashop row (pid 4215) and remove the stale coded identity.
SPECIAL_2514='2514-DRC'

def urlcode(u):
 m=re.search(r'/([0-9]+-[a-z0-9 ]+)(?:-[a-z]+)?(?:$|[/?#])',str(u or '').lower())
 return m.group(1).upper() if m else ''
removed=[]; assigned=[]; corrected=[]
for g in data:
 kept=[]
 for p in g.get('perfumes',[]):
  c=str(p.get('code') or '').strip().upper(); uc=urlcode(p.get('shobiUrl'))
  if not c and uc in REMOVE_EMPTY_URL_CODES:
   removed.append((g.get('brandInfo',{}).get('name',''),p.get('inspiredBy',''),uc)); continue
  if not c and uc in ASSIGN_EMPTY_URL_CODES:
   p['code']=uc; assigned.append((p.get('inspiredBy',''),uc))
  # stale 2514 coded row is the wrong identity; the live empty-code row has pid 4215.
  if c==SPECIAL_2514 and str(p.get('prestashopProductId') or '')!='4215':
   removed.append((g.get('brandInfo',{}).get('name',''),p.get('inspiredBy',''),c)); continue
  if not c and uc==SPECIAL_2514 and str(p.get('prestashopProductId') or '')=='4215':
   p['code']=SPECIAL_2514
   p['inspiredBy']='Sauvage Eau Forte'
   corrected.append(('Sauvage Eau Forte',SPECIAL_2514))
  # Current Shobi canonical code is 1702-KUR; normalize historical URL.
  if str(p.get('code') or '').strip().upper()=='1702-KUR' and uc=='1702-OUD':
   p['shobiUrl']='https://leparfum.com.gr/el/niche-%CE%B1%CF%81%CF%8E%CE%BC%CE%B1%CF%84%CE%B1/1702-kur-oud'
   corrected.append(('Oud Maison Francis Kurkdjian','1702-KUR URL'))
  kept.append(p)
 g['perfumes']=kept
DB.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('removed',len(removed),removed)
print('assigned',len(assigned),assigned)
print('corrected',len(corrected),corrected)
