#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Corrections for which both identity and exact Fragrantica Social Card notes
# were directly verified in the earlier Main Notes pass.
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

# FID-only pass. Main Notes are deliberately frozen here: these entries were
# verified from Shobi identity + the exact Fragrantica perfume page, but their
# Social Card notes are left untouched until the later notes-only audit.
FID_ONLY={
 '1044-CAL': 258,    # Calvin Klein Eternity For Men
 '1057-CAR': 35781,  # Carolina Herrera 212 VIP Men Wild Party
 '1096-DOL': 44035,  # Dolce & Gabbana Light Blue Eau Intense Pour Homme
 '1099-DOL': 2056,   # Dolce & Gabbana The One for Men
 '1134-ARM': 3793,   # Giorgio Armani Emporio Armani Diamonds for Men
 '1190-KEN': 77,     # Kenzo pour Homme
 '1250-RAL': 896,    # Ralph Lauren Safari for Men
}

def code_of(p): return str(p.get('id') or p.get('code') or p.get('shobiCode') or p.get('shobi_code') or '')

def set_fid(p, fid):
 p['fragranticaId']=fid
 if 'fragrantica_id' in p: p['fragrantica_id']=fid
 if 'fid' in p: p['fid']=fid
 p['fragranticaUrl']=f"https://www.fragrantica.com/p/{fid}"

def patch(path):
 data=json.loads(path.read_text(encoding='utf-8'))
 rows=data if isinstance(data,list) else (data.get('perfumes') or data.get('records') or data.get('data') or [])
 if rows and isinstance(rows[0],dict) and isinstance(rows[0].get('perfumes'),list):
  rows=[p for b in rows for p in b.get('perfumes',[])]
 hit=[]
 for p in rows:
  c=code_of(p)
  if c in FIXES:
   f=FIXES[c]
   set_fid(p,f['fid'])
   p['fragranticaSocialCardNotes']=f['notes']
   p['fragranticaSocialCardStatus']='VALIDATED_MANUAL'
   hit.append(c)
  elif c in FID_ONLY:
   set_fid(p,FID_ONLY[c])
   hit.append(c+' (FID only)')
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return hit

for name in ('database_complete.json','database_v2_clean.json'):
 p=ROOT/name
 print(name, patch(p))
