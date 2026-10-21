"""Independently verify the original ZIP before any judging."""
import collections
import hashlib
import json
from pathlib import Path
import random
import zipfile

ROOT=Path(__file__).resolve().parents[2]
S2=ROOT/'stage2'
def read(path): return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l]
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def main():
    for folder in ['results','judgments/batches','judgments/review_batches','metrics','figures','reports','scripts','inputs','logs']:
        (S2/folder).mkdir(parents=True,exist_ok=True)
    archive=ROOT/'HallusionBench_Stage1_Results.zip'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        inventory=json.loads(z.read('PACKAGE_MANIFEST.json'))
        assert len({x['path'] for x in inventory})==len(inventory)
        for item in inventory:
            b=z.read(item['path'])
            assert len(b)==item['bytes'] and sha_bytes(b)==item['sha256'],item['path']
        def j(name): return json.loads(z.read(name))
        def jl(name): return [json.loads(l) for l in z.read(name).decode('utf-8').splitlines() if l]
        rows=jl('results/internvl3_2b_bf16_tiles12/full/responses.jsonl')
        ground=jl('data/manifests/ground_truth.jsonl')
        controls=j('data/manifests/control_groups.json')
        index=j('handoff/stage2_batches/index.json')
        summary=j('handoff/package_summary.json')
        integrity=j('reports/internvl3_2b_bf16_tiles12_integrity.json')
        assert len(rows)==len(ground)==1129
        byid={r['sample_id']:r for r in rows}; gt={r['sample_id']:r for r in ground}
        assert len(byid)==len(gt)==1129 and set(byid)==set(gt)
        assert {r['model_name'] for r in rows}=={'OpenGVLab/InternVL3-2B'}
        assert all(r['status']=='success' and r['model_response_raw'].strip() for r in rows)
        assert len(controls['question_pairs'])==455 and len(controls['figures'])==346 and len(index)==47
        assert sum(r['generation_details']['output_at_token_limit'] for r in rows)==40
        batch_rows=[]
        for entry in index:
            b=z.read(entry['path']); assert sha_bytes(b)==entry['sha256']
            groups=[json.loads(l) for l in b.decode('utf-8').splitlines() if l]
            assert len(groups)==entry['question_groups']
            members=[r for g in groups for r in g['samples']]
            assert len(members)==entry['sample_count']
            batch_rows.extend(members)
        assert len(batch_rows)==1129 and len({r['sample_id'] for r in batch_rows})==1129
        for r in batch_rows:
            sid=r['sample_id']; g=gt[sid]['official_row']
            assert r['model_response_raw']==byid[sid]['model_response_raw']
            for k in ['question','gt_answer','gt_answer_details']: assert r[k]==g[k]
        # Preserve exact, unmodified analysis inputs, sourced from verified ZIP bytes.
        copy_paths=['results/internvl3_2b_bf16_tiles12/full/responses.jsonl','data/manifests/ground_truth.jsonl',
                    'data/manifests/control_groups.json','data/manifests/images.jsonl','handoff/upstream_reference/utils.py',
                    'handoff/upstream_reference/evaluation.py']
        for path in copy_paths: (S2/'inputs'/Path(path).name).write_bytes(z.read(path))
        missing_images=[]
        for image in jl('data/manifests/images.jsonl'):
            p=ROOT/image['path']
            if not p.is_file() or sha_bytes(p.read_bytes())!=image['sha256']: missing_images.append(image['path'])
        assert not missing_images
        report={'archive_sha256':sha_bytes(archive.read_bytes()),'zip_members_verified':len(inventory),
                'sample_count':1129,'unique_ids':1129,'question_control_groups':455,'figure_groups':346,
                'judge_batches':47,'at_token_limit':40,'models':['OpenGVLab/InternVL3-2B'],
                'condition_counts':dict(collections.Counter(r['image_type'] for r in rows)),
                'local_images_hash_verified':346,'smoke_rows_included':0,'other_model_rows_included':0,
                'all_batch_raw_responses_match':True,'all_batch_gt_match':True,
                'package_summary_matches':summary['full_dataset_successful_raw_responses']==1129,
                'stage1_integrity_matches':integrity['complete'], 'passed':True}
        (S2/'reports/stage1_reaudit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        # Pre-register random audit selection before judging; no label information used.
        rng=random.Random(20261021)
        selection=sorted(rng.sample(sorted(byid),113))
        (S2/'judgments/random_review_selection.json').write_text(json.dumps({'seed':20261021,'selection_method':'uniform without replacement before first-pass judging',
                       'count':113,'sample_ids':selection},indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
if __name__=='__main__': main()
