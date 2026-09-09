#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIXES={
 '1048-CAL': {'fid':249,'notes':['Cinnamon','Amber','Vanilla','Sandalwood','Myrrh','Nutmeg']},
 '1064-CHA': {'fid':523,'notes':['Vanilla','Lemon','Peach','Tonka Bean','Ginger','Mandarin Orange']},
 '1074-DRC': {'fid':235,'notes':['Fig Leaf','Fig','Sandalwood','Currant Leaf and Bud','Sage','Rose']},
 '1095-DOL': {'fid':1068,'notes':['Grapefruit','Bergamot','Pepper','Mandarin Orange','Rosemary','Juniper']},
 '1131-ARM': {'fid':414,'notes':['Mandarin Orange','Cedar','Saffron','Musk','Vetiver','Amber']},
 '1504-DON': {'fid':53501,'notes':['Solar Notes','Peach','Orange','Amber','Floral Notes','Pink Pepper']},
 '896-RCAV': {'fid':58538,'notes':['Vanilla','Magnolia','Rose','Patchouli','Cypriol Oil or Nagarmotha','Cedar']},
 '1220-MOS': {'fid':28805,'notes':['Lavender','Cardamom','Cedar','Mandarin Orange','Bergamot','Violet']},
 '500-CHA': {'fid':11,'notes':['Galbanum','Oakmoss','Iris','Hyacinth','Vetiver','Orris Root']},
 '1163-HUG': {'fid':11070,'notes':['Red Apple','Vanilla','Woodsy Notes','Incense','Sichuan Pepper','Coriander']},
 '2234-MON': {'fid':69819,'notes':['Powdery Notes','Vanilla','Heliotrope','Sandalwood','Snow','Amber']},
}
FID_ONLY={
 '130-LEL':23529,'184-YAS':22418,'185-AL HAR':61372,'202-CLIV':4653,
 '362-TMFO':38650,'420-BRB':29562,'456-CAC':12764,'491-CRT':32436,'553-DOL':22955,
 '876-PRA':31044,'900-ROG':17583,'1000-ADO':9783,'1001-ANT':26412,'1044-CAL':258,
 '1076-DRC':228,'1081-DRC':22860,'1196-LAC':41265,'1220-MOS':28805,'1244-PRA':1044,
 '1489-DAV':35819,'1491-CAL':45709,'1494-BOD':31568,'1523-AFN':27357,'1534-SWI':6672,
 '1628-AL HAR':19945,'1636-KIL':31395,'1644-DRC':68415,'1649-GIV':62491,
 '1767-LTN':51016,'1781-LAC':672,'1783-AL HAR':19846,'1808-LTN':40497,
 '1950-SWISA':22928,'2106-MARC':46802,'2133-FRE':2799,'2173-ANFAD':23000,
 '2189-ARM':76171,'2220-AL HAR':19607,'2282-DRC':81847,'2313-DRC':56324,
 '2331-DOL':50207,'2438-KYLJE':90957,'2514-DRC':95863,'-VICT':24876,
 'ALH004':53174,'ALH078':51816,
 '749-KEN':72,'848-NRO':53441,'1043-CAL':275,'1057-CAR':35781,'1096-DOL':44035,
 '1099-DOL':2056,'1134-ARM':3793,'1190-KEN':77,'1250-RAL':896,'735-JIM':27431,'2194-ORT':69923,
}
# Deliberately excluded until the Shobi version is discriminated:
# 1486-TRU (1039 vs 13067), 1629-AL HAR (48224 vs 70385), 2256-GIV (33/40155/17516).

def code_of(p): return str(p.get('id') or p.get('code') or p.get('shobiCode') or p.get('shobi_code') or '')
def set_fid(p,fid):
 p['fragranticaId']=fid
 if 'fragrantica_id' in p:p['fragrantica_id']=fid
 if 'fid' in p:p['fid']=fid
 p['fragranticaUrl']=f"https://www.fragrantica.com/p/{fid}"
def patch(path):
 data=json.loads(path.read_text(encoding='utf-8'))
 rows=data if isinstance(data,list) else (data.get('perfumes') or data.get('records') or data.get('data') or [])
 if rows and isinstance(rows[0],dict) and isinstance(rows[0].get('perfumes'),list):rows=[p for b in rows for p in b.get('perfumes',[])]
 hit=[]
 for p in rows:
  c=code_of(p)
  if c in FIXES:
   f=FIXES[c];set_fid(p,f['fid']);p['fragranticaSocialCardNotes']=f['notes'];p['fragranticaSocialCardStatus']='VALIDATED_MANUAL';hit.append(c)
  elif c in FID_ONLY:set_fid(p,FID_ONLY[c]);hit.append(c+' (FID only)')
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return hit
for name in ('database_complete.json','database_v2_clean.json'):
 p=ROOT/name;print(name,patch(p))