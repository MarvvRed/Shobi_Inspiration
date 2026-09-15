#!/usr/bin/env python3
import json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V=json.loads((ROOT/'database/fragrantica/social-cards/records/social-card-main-notes-validated.json').read_text(encoding='utf-8'))
pat=Counter();by_count=defaultdict(Counter);examples=defaultdict(list)
for x in V:
 if x.get('validated') is not True:continue
 slots=x.get('validatedSlots') or []
 positions=tuple(int(s.get('slot') or 0) for s in slots if int(s.get('slot') or 0)>0)
 notes=x.get('mainNotes') or []
 if not positions and x.get('rawSlots'):
  positions=tuple(int(s.get('slot') or 0) for s in x['rawSlots'] if int(s.get('slot') or 0)>0)
 if not positions:continue
 pat[positions]+=1;by_count[len(notes)][positions]+=1
 if len(examples[(len(notes),positions)])<5:examples[(len(notes),positions)].append({'code':x.get('code'),'fid':x.get('fragranticaId'),'notes':notes})
out={'validatedWithSlotPattern':sum(pat.values()),'byCount':{str(k):[{'slots':list(p),'count':n,'examples':examples[(k,p)]} for p,n in c.most_common()] for k,c in sorted(by_count.items())},'allPatterns':[{'slots':list(p),'count':n} for p,n in pat.most_common()]}
(ROOT/'database/audits/validated-note-slot-patterns.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Validated note slot patterns','',f"- Cards with known slot pattern: **{out['validatedWithSlotPattern']}**",'']
for k,items in out['byCount'].items():
 lines.append(f'## {k} notes')
 for it in items[:10]:lines.append(f"- slots {it['slots']}: **{it['count']}**")
 lines.append('')
(ROOT/'database/audits/validated-note-slot-patterns.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({k:[(x['slots'],x['count']) for x in v[:5]] for k,v in out['byCount'].items()},indent=2))
