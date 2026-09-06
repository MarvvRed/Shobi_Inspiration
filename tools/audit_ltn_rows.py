import json
from pathlib import Path

def walk(x):
    if isinstance(x,list):
        for v in x: yield from walk(v)
    elif isinstance(x,dict):
        code = str(x.get('Code') or x.get('code') or x.get('Shobi Code') or x.get('shobi_code') or '').strip()
        if code in {'2783-LTN','2786-LTN','2791-LTN'}:
            yield x
        for v in x.values(): yield from walk(v)

data=json.loads(Path('database_complete.json').read_text(encoding='utf-8-sig'))
rows=list(walk(data))
Path('ltn-row-audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
