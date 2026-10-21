"""Verify both original archives and export an image-safe publication snapshot.

Never changes responses, GT, saved judgments, or their local archives.
"""
import collections,hashlib,json,re,shutil,zipfile
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'publication/HallusionBench-InternVL3-2B-Reproduction'
AUDIT=ROOT/'reports/stage3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]
def dump(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
def main():
    AUDIT.mkdir(exist_ok=True)
    keys=['results/internvl3_2b_bf16_tiles12/full/responses.jsonl','data/manifests/ground_truth.jsonl','data/manifests/inference.jsonl','stage2/results/judgments.jsonl','stage2/results/pair_relations.jsonl']
    initial={s:sha(ROOT/s) for s in keys};p=AUDIT/'immutable_inputs.json'
    if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==initial
    else:dump(p,initial)
    candidates=set();archives=[];local_diffs=[]
    for name in ['HallusionBench_Stage1_Results.zip','HallusionBench_Stage2_Results.zip']:
        with zipfile.ZipFile(ROOT/name) as z:
            assert z.testzip() is None
            inventory=json.loads(z.read('PACKAGE_MANIFEST.json' if 'Stage1' in name else 'stage2/PACKAGE_MANIFEST.json'))
            if isinstance(inventory,dict):inventory=inventory['files']
            for f in inventory:
                body=z.read(f['path']);assert hashlib.sha256(body).hexdigest()==f['sha256']
                assert len(body)==f.get('bytes',f.get('size'))
                candidates.add(f['path'])
                local=ROOT/f['path']
                if not local.exists() or sha(local)!=f['sha256']:local_diffs.append({'archive':name,'path':f['path'],'local_exists':local.exists()})
            archives.append({'archive':name,'sha256':sha(ROOT/name),'payload_files_verified':len(inventory),'crc_passed':True})
    source=rows(ROOT/keys[0]);judged=rows(ROOT/keys[3]);gt=rows(ROOT/keys[1]);groups=json.loads((ROOT/'data/manifests/control_groups.json').read_text(encoding='utf-8'))
    ids={r['sample_id'] for r in source};truth={r['sample_id']:r['official_row'] for r in gt};answers={r['sample_id']:r for r in source}
    assert len(source)==len(judged)==len(gt)==len(ids)==1129
    assert ids==set(truth)=={r['sample_id'] for r in judged}
    for r in judged:
        assert r['model_response_raw']==answers[r['sample_id']]['model_response_raw']
        for k in ['question','gt_answer','gt_answer_details']:assert r[k]==truth[r['sample_id']][k]
    images=rows(ROOT/'data/manifests/images.jsonl');assert len(images)==346
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in images)
    originals={p for r in source if r['image_type']=='original' for p in r['image_paths']};edits={p for r in source if r['image_type']=='edited' for p in r['image_paths']}
    assert len(originals)==165 and len(edits)==181
    assert len(groups['question_pairs'])==455 and len(groups['figures'])==346
    assert len(list((ROOT/'stage2/judgments/batches').glob('batch_*.jsonl')))==47
    assert sum(len(rows(p)) for p in (ROOT/'stage2/judgments/second_pass').glob('chunk_*.jsonl'))==397
    assert sum(len(rows(p)) for p in (ROOT/'stage2/judgments/consistency_v2').glob('batch_*.jsonl'))==1129
    assert len(rows(ROOT/'stage2/results/pair_relations.jsonl'))==674
    assert len(rows(ROOT/'stage2/judgments/unresolved_samples.jsonl'))==32
    assert len(rows(ROOT/'stage2/results/explanation_issues.jsonl'))==87
    assert len(list((ROOT/'stage2/figures').glob('*.png')))==8
    assert len(json.loads((ROOT/'stage2/reports/case_studies.json').read_text(encoding='utf-8')))==6
    assert len(PdfReader(ROOT/'stage2/reports/HallusionBench_Stage2_Report_zhTW.pdf').pages)==20
    DEST.mkdir(parents=True,exist_ok=True)
    excluded=[];redacted=[];copied=[]
    immutable=set(keys)|{'stage2/inputs/responses.jsonl','stage2/inputs/ground_truth.jsonl'}
    for rel in sorted(candidates):
        src=ROOT/rel
        if not src.is_file():raise FileNotFoundError(src)
        if src.suffix.lower()=='.pdf' or '/figures/cases/' in rel or rel=='handoff/upstream_reference/README.md':
            excluded.append({'path':rel,'sha256':sha(src),'reason':'third-party images, embedded image report, or upstream README embeds; retained locally; metadata retained'})
            continue
        dest=DEST/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        data=src.read_bytes()
        if rel not in immutable and src.suffix.lower() not in ['.png','.pdf']:
            try:
                text=data.decode('utf-8-sig')
                # Retain all GPU/experiment values, replace only user-directory names in diagnostic logs.
                new,count=re.subn(r'(?i)([A-Z]:[\\/]+Users[\\/]+)(?!Public\b|Default\b)[^\\/\s"<>]+',r'\1USER',text)
                if count:
                    data=new.encode('utf-8');redacted.append({'path':rel,'replacement_count':count,'source_sha256':sha(src),'published_sha256':hashlib.sha256(data).hexdigest(),'reason':'local Windows account directory name removed; experiment values unchanged'})
            except UnicodeDecodeError:pass
        if not dest.exists():dest.write_bytes(data)
        else:assert dest.read_bytes()==data,('Existing export was edited; do not overwrite',rel)
        copied.append(rel)
    for rel,h in initial.items():assert sha(DEST/rel)==h
    dump(AUDIT/'source_audit.json',{'passed':True,'archives':archives,'local_vs_archive_differences':local_diffs,'responses':1129,'final_judgments':1129,'question_control_groups':455,'figure_groups':346,'original_images':165,'edited_images':181,'source_images_rehashed':346,'initial_batches':47,'historical_review_items':397,'v2_audit_items':1129,'pairs':674,'reference_disputes':32,'explanation_issues':87,'charts':8,'cases':6,'local_original_report_pages':20,'exported_source_files':len(copied),'excluded':excluded,'privacy_redactions':redacted,'raw_outputs_GT_final_labels_unchanged':True,'GPU_inference_performed':False,'new_semantic_judging_performed':False})
    target=DEST/'reports/stage3';target.mkdir(exist_ok=True)
    for name in ['source_audit.json','immutable_inputs.json']:shutil.copyfile(AUDIT/name,target/name)
    for name in ['.gitignore','.gitattributes']:
        if not (DEST/name).exists():shutil.copyfile(ROOT/name,DEST/name)
    print(json.dumps({'passed':True,'publication_directory':str(DEST),'source_files':len(copied),'excluded':len(excluded),'redacted_diagnostic_files':len(redacted),'local_vs_archive_differences':local_diffs},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
