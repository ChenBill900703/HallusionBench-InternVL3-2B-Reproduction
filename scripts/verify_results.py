"""Data/coverage checks only. Never parses or grades an answer."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
def sha(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def verify(run_name, strict=False):
    manifest = read(ROOT/'data/manifests/inference.jsonl')
    ground = read(ROOT/'data/manifests/ground_truth.jsonl')
    expected = {r['sample_id']:r for r in manifest}
    gt = {r['sample_id']:r for r in ground}
    assert len(expected)==len(manifest)==len(gt)==len(ground)==1129
    assert set(expected)==set(gt)
    groups = json.loads((ROOT/'data/manifests/control_groups.json').read_text(encoding='utf-8'))
    assert len(groups['question_pairs'])==455 and len(groups['figures'])==346
    assert set(s for ids in groups['question_pairs'].values() for s in ids)==set(expected)
    assert sum(len(v) for v in groups['question_pairs'].values())==1129
    assert sum(len(v) for v in groups['figures'].values())==951
    image_errors=[]
    for image in read(ROOT/'data/manifests/images.jsonl'):
        path=ROOT/image['path']
        if not path.exists() or sha(path)!=image['sha256']: image_errors.append(image['path'])
    path=ROOT/'results'/run_name/'full/responses.jsonl'
    rows=read(path) if path.exists() else []
    counts=collections.Counter(r['sample_id'] for r in rows)
    actual={r['sample_id']:r for r in rows}
    errors=[]
    manifest_sha=sha(ROOT/'data/manifests/inference.jsonl')
    for r in rows:
        sid=r['sample_id']
        if sid not in expected:
            errors.append([sid,'unexpected_sample']); continue
        source=expected[sid]
        for k in ['question','image_paths','image_sha256','category','subcategory','question_pair_id','figure_id','original_question_metadata']:
            if r[k]!=source[k]: errors.append([sid,'metadata_mismatch',k])
        if r['inference_manifest_sha256']!=manifest_sha: errors.append([sid,'manifest_sha_mismatch'])
        if r['prompt_text']!=r['inference_parameters']['prompt_template'].format(question=source['question']): errors.append([sid,'prompt_mismatch'])
        if r['status']=='success':
            if not isinstance(r['model_response_raw'],str) or not r['model_response_raw'].strip(): errors.append([sid,'empty_success'])
            details=r['generation_details']
            if not details or not details.get('generated_token_ids'): errors.append([sid,'missing_output_token_ids'])
            patches=details.get('image_patch_counts',details.get('image_grid_thw',[]))
            if r['image_type']=='no_visual' and (r['image_paths'] or patches): errors.append([sid,'unexpected_visual_input'])
            if r['image_type']!='no_visual' and not patches: errors.append([sid,'missing_visual_input'])
        def no_gt(value):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k.startswith('gt_'): errors.append([sid,'ground_truth_leak_field',k])
                    no_gt(v)
            elif isinstance(value,list):
                for v in value: no_gt(v)
        no_gt(r)
    missing=sorted(set(expected)-set(actual))
    duplicates=[k for k,n in counts.items() if n>1]
    failures=[{'sample_id':r['sample_id'],'status':r['status'],'error_message':r['error_message']} for r in rows if r['status']!='success']
    csv_path=path.with_suffix('.csv')
    if rows:
        if not csv_path.is_file():
            errors.append(['csv','missing_file'])
        else:
            with open(csv_path,encoding='utf-8-sig',newline='') as f: csv_rows=list(csv.DictReader(f))
            if len(csv_rows)!=len(rows): errors.append(['csv','row_count_mismatch'])
            else:
                for row,csv_row in zip(rows,csv_rows):
                    if row['sample_id']!=csv_row['sample_id'] or (row['model_response_raw'] or '')!=csv_row['model_response_raw']:
                        errors.append([row['sample_id'],'csv_raw_response_mismatch'])
    cap=[r['sample_id'] for r in rows if (r.get('generation_details') or {}).get('output_at_token_limit')]
    result={'run_name':run_name,'expected_count':1129,'record_count':len(rows),
            'successful_response_count':sum(r['status']=='success' for r in rows),
            'missing_sample_ids':missing,'duplicate_sample_ids':duplicates,'failures':failures,
            'image_hash_errors':image_errors,'structural_errors':errors,'outputs_at_token_limit':cap,
            'status_counts':dict(collections.Counter(r['status'] for r in rows)),
            'condition_counts':dict(collections.Counter(r['image_type'] for r in rows if r['status']=='success')),
            'total_inference_seconds':sum(r['inference_time'] for r in rows),
            'max_peak_allocated_gib':max((r['peak_vram_allocated_bytes'] for r in rows),default=0)/1024**3,
            'max_peak_reserved_gib':max((r['peak_vram_reserved_bytes'] for r in rows),default=0)/1024**3,
            'response_file_sha256':sha(path) if path.exists() else None,
            'answer_correctness_evaluated':False,
            'complete':not(missing or duplicates or failures or image_errors or errors) and len(rows)==1129}
    (ROOT/'reports'/f'{run_name}_integrity.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'missing_sample_ids','outputs_at_token_limit'}},indent=2))
    if strict and not result['complete']: raise SystemExit('Full coverage/integrity checks did not pass.')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-name',default='internvl3_2b_bf16_tiles12')
    p.add_argument('--strict',action='store_true')
    a=p.parse_args()
    verify(a.run_name,a.strict)
