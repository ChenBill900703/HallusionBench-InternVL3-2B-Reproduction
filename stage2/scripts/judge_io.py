"""Persistence and display only: semantic labels are authored by the in-session judge."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]; S2=ROOT/'stage2'
STANCES={'y':'yes','n':'no','u':'uncertain','a':'ambiguous'}
REL={'s':'same','d':'different','u':'uncertain'}
def read(p): return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l]
def atomic(p,rows):
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8'); tmp.replace(p)
def show(batch):
    groups=read(ROOT/f'handoff/stage2_batches/batch_{batch:03d}.jsonl')
    i=0
    for group in groups:
        print('GROUP',group['question_pair_id'])
        for r in group['samples']:
            print(f"[{i}] {r['sample_id']} ({r['image_type']}) CAP={r['output_at_token_limit']}\nQ: {r['question']}\nREF[{r['gt_answer']}]: {r['gt_answer_details']}\nA: {r['model_response_raw']}")
            i+=1
def save(batch,decisions,pairs):
    source=ROOT/f'handoff/stage2_batches/batch_{batch:03d}.jsonl'
    groups=read(source); inputs=[r for g in groups for r in g['samples']]
    assert len(decisions)==len(inputs),(len(decisions),len(inputs))
    identity=json.loads((S2/'judgments/judge_identity.json').read_text(encoding='utf-8'))
    now=datetime.now(timezone.utc).isoformat()
    rows=[]
    for i,(r,d) in enumerate(zip(inputs,decisions)):
        # Each decision: [stance code, semantic label, concise reason, optional review issue].
        stance,sem,reason=d[:3]; issue=d[3] if len(d)>3 else ''
        assert stance in STANCES and sem in [0,1,2] and reason
        final=int(sem==1 or (r['category']=='VS' and str(r['figure_id'])=='0' and sem==2))
        rows.append({**r,'batch':batch,'batch_row_index':i,'judge_model':identity['model'],
                     'judge_method':'in-session semantic review of full question, reference and complete raw response; no API',
                     'judge_prompt_version':'hb-semantic-v1','predicted_stance':STANCES[stance],
                     'semantic_correctness':sem,'final_binary_correctness':final,
                     'requires_review':bool(issue) or stance in ['u','a'] or r['output_at_token_limit'],
                     'review_reason':issue or ('output_limit' if r['output_at_token_limit'] else 'uncertain_or_ambiguous_stance' if stance in ['u','a'] else ''),
                     'short_explanation':reason,'judged_at_utc':now,'source_batch_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    # Relation entries refer to local batch indices; baseline identity is explicit, never estimated.
    lookup={i:r for i,r in enumerate(inputs)}; expected=[]; group_indices={}; offset=0
    for g in groups:
        ids=list(range(offset,offset+len(g['samples']))); group_indices[g['question_pair_id']]=ids
        baseline=next(i for i in ids if str(lookup[i]['figure_id'])=='0')
        expected.extend((baseline,i) for i in ids if i!=baseline); offset+=len(ids)
    assert {(a,b) for a,b,*_ in pairs}==set(expected),('pair relations missing or duplicated',batch)
    assert len(pairs)==len(expected)
    relations=[]
    for a,b,rel,reason in pairs:
        assert rel in REL and reason
        relations.append({'baseline_sample_id':lookup[a]['sample_id'],'sample_id':lookup[b]['sample_id'],
                          'question_pair_id':next(g for g,indices in group_indices.items() if a in indices),
                          'relation':REL[rel],'reason':reason,'judge_model':identity['model'],
                          'judge_method':'semantic non-contradiction review, full responses visible; no API',
                          'judge_prompt_version':'hb-same-v1','requires_review':rel=='u','judged_at_utc':now})
    out=S2/f'judgments/batches/batch_{batch:03d}.jsonl'
    relout=S2/f'judgments/batches/pairs_{batch:03d}.jsonl'
    if out.exists() or relout.exists(): raise ValueError('Do not overwrite an already saved batch; use an adjudication record.')
    atomic(out,rows); atomic(relout,relations)
    rebuild()
    print(f'Saved batch {batch}: {len(rows)} semantic judgments, {len(relations)} pair relations.')
def rebuild():
    progress_path=S2/'judgments/progress.json'
    if progress_path.exists() and json.loads(progress_path.read_text(encoding='utf-8')).get('quality_review_complete'):
        raise ValueError('Adjudication already complete. Use finalize_judgments.py; do not overwrite final results with first-pass labels.')
    rows=[r for p in sorted((S2/'judgments/batches').glob('batch_*.jsonl')) for r in read(p)]
    pairs=[r for p in sorted((S2/'judgments/batches').glob('pairs_*.jsonl')) for r in read(p)]
    assert len({r['sample_id'] for r in rows})==len(rows)
    atomic(S2/'results/judgments.jsonl',rows)
    atomic(S2/'results/pair_relations.jsonl',pairs)
    progress={'completed_batches':len(list((S2/'judgments/batches').glob('batch_*.jsonl'))),
              'judged_samples':len(rows),'expected_samples':1129,'nonbaseline_pair_relations':len(pairs),
              'first_pass_complete':len(rows)==1129,'quality_review_complete':False}
    (S2/'judgments/progress.json').write_text(json.dumps(progress,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['show','save','rebuild']); p.add_argument('batch',nargs='?',type=int); p.add_argument('labels',nargs='?')
    a=p.parse_args()
    if a.command=='show': show(a.batch)
    elif a.command=='save':
        labels=json.loads(Path(a.labels).read_text(encoding='utf-8')); save(a.batch,labels['decisions'],labels['pairs'])
    else: rebuild()
