"""Blinded display/checkpointing. No semantic classifier is implemented here."""
import argparse,json,hashlib,re
from pathlib import Path
from datetime import datetime,timezone
from judge_io import read,atomic,STANCES,ROOT,S2
QCD=S2/'judgments/second_pass'; QCD.mkdir(exist_ok=True)
def selection():
    rows=read(S2/'results/judgments.jsonl')
    ids=set(json.loads((S2/'judgments/random_review_selection.json').read_text(encoding='utf-8'))['sample_ids'])
    selected=[]
    for r in rows:
        reasons=[]
        if r['sample_id'] in ids: reasons.append('preregistered_random_10_percent')
        if r['requires_review']: reasons.append('first_pass_flag')
        if re.match(r'^(which|what|who|where|when|how many)\b',r['question'],re.I): reasons.append('nonbinary_question_candidate')
        if reasons: selected.append({'sample_id':r['sample_id'],'selection_reasons':reasons})
    return selected
def prepare():
    p=QCD/'selection.json'
    if p.exists(): raise ValueError('Selection already persisted')
    rows=selection()
    p.write_text(json.dumps({'chunk_size':20,'selected':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print('QC selected',len(rows),'chunks',(len(rows)+19)//20)
def chunk(n):
    selected=json.loads((QCD/'selection.json').read_text(encoding='utf-8'))['selected'][(n-1)*20:n*20]
    lookup={r['sample_id']:r for p in sorted((S2/'judgments/batches').glob('batch_*.jsonl')) for r in read(p)}
    return [lookup[r['sample_id']] for r in selected]
def show(n):
    for i,r in enumerate(chunk(n)):
        print(f"[{i}] {r['sample_id']} {r['image_type']} CAP={r['output_at_token_limit']}\nQ: {r['question']}\nREF[{r['gt_answer']}]: {r['gt_answer_details']}\nA: {r['model_response_raw']}")
def save(n,path):
    data=json.loads(Path(path).read_text(encoding='utf-8')); rows=chunk(n)
    assert len(data['decisions'])==len(rows)
    dest=QCD/f'chunk_{n:03d}.jsonl'
    assert not dest.exists(),'Do not overwrite second-pass observations'
    out=[]
    for r,d in zip(rows,data['decisions']):
        s,c,reason=d[:3]; assert s in STANCES and c in [0,1,2]
        issue=d[3] if len(d)>3 else ''
        out.append({'sample_id':r['sample_id'],'predicted_stance':STANCES[s],'semantic_correctness':c,
                    'short_explanation':reason,'unresolved_issue':issue,
                    'review_method':'same-model second reading; prior labels hidden in display; not independent human validation',
                    'judge_model':'gpt-6.1-sol','reviewed_at_utc':datetime.now(timezone.utc).isoformat(),
                    'input_sha256':hashlib.sha256(json.dumps({k:r[k] for k in ['sample_id','question','gt_answer','gt_answer_details','model_response_raw']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()})
    atomic(dest,out);print('Saved QC chunk',n,len(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','show','save']);p.add_argument('n',type=int,nargs='?');p.add_argument('path',nargs='?');a=p.parse_args()
    if a.command=='prepare':prepare()
    elif a.command=='show':show(a.n)
    else:save(a.n,a.path)
