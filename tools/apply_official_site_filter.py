from pathlib import Path

path = Path('script.js')
text = path.read_text(encoding='utf-8')
old = "        const rawData = await response.json();\n"
new = "        const rawDataAll = await response.json();\n        const isOfficialPerfume = (p) => {\n            const status = String((p && (p.fragrantica_status || p.fragranticaStatus)) || '').toUpperCase();\n            return !status.startsWith('RESOLVED_NO_FORCE');\n        };\n        const rawData = (Array.isArray(rawDataAll) && rawDataAll.length > 0 && Array.isArray(rawDataAll[0]?.perfumes))\n            ? rawDataAll.map(brandObject => ({ ...brandObject, perfumes: (brandObject.perfumes || []).filter(isOfficialPerfume) }))\n            : (Array.isArray(rawDataAll) ? rawDataAll.filter(isOfficialPerfume) : rawDataAll);\n"
if new in text:
    raise SystemExit('Official filter already applied')
if old not in text:
    raise SystemExit('Expected rawData load line not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
