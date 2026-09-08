#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIX={
'646-ARM':('Giorgio Armani','Armani Code for Women',413,'https://www.fragrantica.com/perfume/Giorgio-Armani/Armani-Code-for-Women-413.html'),
'716-ISS':('Issey Miyake','A Scent by Issey Miyake',6432,'https://www.fragrantica.com/perfume/Issey-Miyake/A-Scent-by-Issey-Miyake-6432.html'),
'847-NRO':('Narciso Rodriguez','Narciso Poudree',36679,'https://www.fragrantica.com/perfume/Narciso-Rodriguez/Narciso-Poudree-36679.html'),
'866-PAC':('Paco Rabanne','Ultraviolet',519,'https://www.fragrantica.com/perfume/Paco-Rabanne/Ultraviolet-519.html'),
'1165-HUG':('Hugo Boss','Hugo Energise',569,'https://www.fragrantica.com/perfume/Hugo-Boss/Hugo-Energise-569.html'),
'1189-KEN':('Kenzo','Kenzo Homme Sport Extreme',18174,'https://www.fragrantica.com/perfume/Kenzo/Kenzo-Homme-Sport-Extreme-18174.html'),
'1281-YZLO':('Yves Saint Laurent',"L'Homme Parfum Intense",18841,'https://www.fragrantica.com/perfume/Yves-Saint-Laurent/L-Homme-Parfum-Intense-18841.html'),
'1890-LEL':('Le Labo','Lys 41',18382,'https://www.fragrantica.com/perfume/Le-Labo/Lys-41-18382.html'),
'2265-KAY':('Kayali Fragrances','Oudgasm Rose Oud 16 Eau de Parfum Intense',85186,'https://www.fragrantica.com/perfume/Kayali-Fragrances/Oudgasm-Rose-Oud-16-Eau-de-Parfum-Intense-85186.html')}
for fn in ('database_complete.json','database_v2_clean.json'):
 p=ROOT/fn; data=json.loads(p.read_text(encoding='utf-8')); rows=data if isinstance(data,list) else data.get('perfumes',[]); changed=[]
 for r in rows:
  c=str(r.get('code') or '')
  if c not in FIX: continue
  b,n,i,u=FIX[c]; old=(r.get('brand'),r.get('inspiredBy'),r.get('fragranticaId'),r.get('fragranticaUrl'))
  r['brand']=b; r['inspiredBy']=n; r['fragranticaId']=i; r['fragranticaUrl']=u; changed.append((c,old,i))
 if len(changed)!=9: raise SystemExit(f'{fn}: expected 9 changes, got {len(changed)}')
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(fn,len(changed))
