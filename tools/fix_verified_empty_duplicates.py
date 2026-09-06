import json
from pathlib import Path

DB=Path('database_complete.json')
data=json.loads(DB.read_text(encoding='utf-8'))

# Empty-code Prestashop rows independently verified as the same real Shobi
# perfume already represented by the coded catalog row.
TARGETS={
 '3485': ('Marc-Antoine Barrois','B683 Eau de Parfum','2106-MARC'),
 '3645': ('Anfasic Dokhoon','Sukar Eau de Parfum','2173-ANFAD'),
 '2911': ('Al Haramain','Sultan Concentrated Perfume Oil','1783-AL HAR'),
 '2334': ('Al Haramain','Wardia / Twin Flower','1628-AL HAR'),
 '2271': ('Al Haramain','Mukhallath Al Emirates Perfume Oil','1526-AL HAR'),
}

codes={str(p.get('code') or '').strip().upper() for g in data for p in g.get('perfumes',[]) if str(p.get('code') or '').strip()}
missing=[v[2] for v in TARGETS.values() if v[2] not in codes]
if missing:
 raise SystemExit('Refusing cleanup: coded counterparts missing: '+', '.join(missing))

removed=[]
for g in data:
 kept=[]
 for p in g.get('perfumes',[]):
  pid=str(p.get('prestashopProductId') or '').strip()
  code=str(p.get('code') or '').strip()
  if not code and pid in TARGETS:
   removed.append((pid,g.get('brandInfo',{}).get('name',''),p.get('inspiredBy',''),TARGETS[pid][2]))
   continue
  kept.append(p)
 g['perfumes']=kept

if len(removed)!=len(TARGETS):
 raise SystemExit(f'Refusing partial cleanup: expected {len(TARGETS)} removals, got {len(removed)}: {removed}')

DB.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('removed',len(removed))
for x in removed: print(x)
