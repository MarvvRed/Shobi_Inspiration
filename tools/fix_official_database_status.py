from pathlib import Path

TARGET_ID = 'pid:2688'
OLD_STATUS = 'NEEDS_REVERIFICATION'
NEW_STATUS = 'VERIFIED_LOCAL_CORPUS_V2'

path = Path('database_complete.json')
text = path.read_text(encoding='utf-8')

id_tokens = [
    f'"id": "{TARGET_ID}"',
    f'"id":"{TARGET_ID}"',
    f'"code": "{TARGET_ID}"',
    f'"code":"{TARGET_ID}"',
]
pos = next((text.find(token) for token in id_tokens if text.find(token) != -1), -1)
if pos == -1:
    raise SystemExit(f'{TARGET_ID} not found in database_complete.json')

start = max(0, pos - 12000)
end = min(len(text), pos + 12000)
window = text[start:end]

old_patterns = [
    f'"fragrantica_status": "{OLD_STATUS}"',
    f'"fragrantica_status":"{OLD_STATUS}"',
    f'"fragranticaStatus": "{OLD_STATUS}"',
    f'"fragranticaStatus":"{OLD_STATUS}"',
]
found = [(p, window.count(p)) for p in old_patterns if p in window]
if sum(c for _, c in found) != 1:
    raise SystemExit(f'Expected exactly one {OLD_STATUS} near {TARGET_ID}, found {found}')

old_pattern = found[0][0]
new_pattern = old_pattern.replace(OLD_STATUS, NEW_STATUS)
window = window.replace(old_pattern, new_pattern, 1)
updated = text[:start] + window + text[end:]

if updated == text:
    raise SystemExit('No change made')

path.write_text(updated, encoding='utf-8')
print(f'Updated {TARGET_ID}: {OLD_STATUS} -> {NEW_STATUS}')
