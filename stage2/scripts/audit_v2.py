"""Display and persist manually authored full-corpus consistency audit. No classifier/API."""
import argparse, json, hashlib, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timezone
from judge_io import S2, ROOT, read, atomic, STANCES, REL
D = S2/'judgments/consistency_v2'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    D.mkdir(exist_ok=True)
    old=D/'prior_final';old.mkdir(exist_ok=True)
    for source in [S2/'results/judgments.jsonl',S2/'results/pair_relations.jsonl',S2/'reports/judge_quality.json',S2/'metrics/overall.json',S2/'judgments/RUBRIC.md']:
        dest=old/source.name
        if not dest.exists(): shutil.copyfile(source,dest)
    rubric=D/'RUBRIC_v2.md'
    assert rubric.exists()
    config={'rubric_sha256':sha(rubric),'previous_judgments_sha256':sha(old/'judgments.jsonl'),
            'previous_pairs_sha256':sha(old/'pair_relations.jsonl'),'scope':'all 1129 full responses and 674 nonbaseline comparisons',
            'prior_labels_visible':True,'independent':False,'human_validation':False,
            'method':'in-session semantic consistency audit; manually authored exceptions; no paid API; no classifier',
            'reference_priority':'gt_answer_details; binary GT preserved for official metrics and dispute sensitivity'}
    p=D/'audit_config.json'
    if p.exists(): assert json.loads(p.read_text(encoding='utf-8'))==config
    else:p.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Frozen source and rubric. 47 complete batches required.')
def sources(n):
    rows=[r for r in read(D/'prior_final/judgments.jsonl') if r['batch']==n]
    ids={r['sample_id'] for r in rows}
    pairs=[r for r in read(D/'prior_final/pair_relations.jsonl') if r['sample_id'] in ids]
    return rows,pairs
def show(n):
    rows,pairs=sources(n);idx={r['sample_id']:i for i,r in enumerate(rows)}
    for i,r in enumerate(rows):
        print(f"[{i}] {r['sample_id']} old={r['predicted_stance']}/{r['semantic_correctness']} CAP={int(r['output_at_token_limit'])}\nQ:{r['question']}\nR[{r['gt_answer']}]:{r['gt_answer_details']}\nA:{r['model_response_raw']}")
    print('PAIRS baseline>current: '+ '; '.join(f"{idx[r['baseline_sample_id']]}>{idx[r['sample_id']]}:{r['relation']}" for r in pairs))
def save(n,path):
    rows,pairs=sources(n);labels=json.loads(Path(path).read_text(encoding='utf-8'))
    assert labels['reviewed_all_full_text'] is True
    config=json.loads((D/'audit_config.json').read_text(encoding='utf-8'))
    assert config['rubric_sha256']==sha(D/'RUBRIC_v2.md')
    overrides={int(k):v for k,v in labels.get('overrides',{}).items()}
    notes={int(k):v for k,v in labels.get('notes',{}).items()}
    assert set(overrides)|set(notes)<=set(range(len(rows)))
    out=[];now=datetime.now(timezone.utc).isoformat()
    for i,r in enumerate(rows):
        d=overrides.get(i)
        if d: assert d[0] in STANCES and d[1] in [0,1,2] and d[2]
        out.append({'sample_id':r['sample_id'],'predicted_stance':STANCES[d[0]] if d else r['predicted_stance'],
                    'semantic_correctness':d[1] if d else r['semantic_correctness'],
                    'short_explanation':d[2] if d else r['short_explanation'],
                    'audit_note':notes.get(i,''),'decision':'revised' if d else 'affirmed_after_full_text_review',
                    'rubric_version':'hb-semantic-v2','rubric_sha256':config['rubric_sha256'],
                    'source_sha256':hashlib.sha256(json.dumps({k:r[k] for k in ['sample_id','question','gt_answer','gt_answer_details','model_response_raw']},ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                    'audited_at_utc':now,'prior_labels_visible':True})
    index={r['sample_id']:i for i,r in enumerate(rows)}
    pmap={index[r['sample_id']]:r for r in pairs}
    po={int(k):v for k,v in labels.get('pairs',{}).items()};assert set(po)<=set(pmap)
    relout=[]
    for i,r in pmap.items():
        d=po.get(i)
        if d:assert d[0] in REL and d[1]
        relout.append({**r,'relation':REL[d[0]] if d else r['relation'],'reason':d[1] if d else r['reason'],
                       'judge_prompt_version':'hb-same-v2','audit_decision':'revised' if d else 'affirmed_after_full_text_review',
                       'prior_labels_visible':True,'audited_at_utc':now})
    dest=D/f'batch_{n:03d}.jsonl';pd=D/f'pairs_{n:03d}.jsonl'
    assert not dest.exists() and not pd.exists(),'Immutable audit checkpoint already exists'
    atomic(dest,out);atomic(pd,relout)
    print('Audit saved',n,len(out),'items',len(relout),'relations;',len(overrides),'item revisions',len(po),'relation revisions')
from pathlib import Path
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','show','save']);p.add_argument('n',type=int,nargs='?');p.add_argument('path',nargs='?');a=p.parse_args()
    if a.command=='prepare':prepare()
    elif a.command=='show':show(a.n)
    else:save(a.n,a.path)
