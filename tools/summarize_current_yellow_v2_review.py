#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'database/audits/current-yellow-v2-exact-validation.json'
OUT=ROOT/'database/audits/current-yellow-v2-review-summary.json'


def main():
    data=json.loads(SRC.read_text(encoding='utf-8'))
    rows=[r for r in data.get('rows',[]) if r.get('status')=='REVIEW']
    fail_labels=[]
    rows_by_failed_count=Counter()
    note_failures=Counter()
    failure_modes=Counter()
    near_pass=[]
    for r in rows:
        failed=[]
        for lab in r.get('labels',[]):
            if lab.get('ok'):
                continue
            failed.append(lab)
            note=str(lab.get('note') or '')
            note_failures[note]+=1
            exact=int(lab.get('exactReads') or 0)
            crop=int(lab.get('exactCropReads') or 0)
            comp=int(lab.get('competingEligibleReads') or 0)
            if exact < 2:
                failure_modes['LT_2_EXACT_READS']+=1
            if crop < 1:
                failure_modes['NO_EXACT_CROP_READ']+=1
            if comp > 0:
                failure_modes['COMPETING_ELIGIBLE_READS']+=1
            fail_labels.append({'code':r.get('code'),'fid':r.get('fid'),'note':note,'exactReads':exact,'exactCropReads':crop,'competingEligibleReads':comp})
        rows_by_failed_count[len(failed)]+=1
        if len(failed)==1:
            near_pass.append({'code':r.get('code'),'fid':r.get('fid'),'failedLabel':failed[0]})
    payload={
        'reviewRows':len(rows),
        'failedLabels':len(fail_labels),
        'rowsByFailedLabelCount':dict(sorted(rows_by_failed_count.items())),
        'failureModes':dict(failure_modes),
        'topFailedNotes':note_failures.most_common(30),
        'nearPassRows':near_pass,
        'failedLabelDetails':fail_labels,
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:payload[k] for k in ('reviewRows','failedLabels','rowsByFailedLabelCount','failureModes','topFailedNotes')},ensure_ascii=False))

if __name__=='__main__': main()
