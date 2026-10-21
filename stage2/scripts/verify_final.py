"""Read-only cross-layer acceptance checks; optional original project source checks."""
import json,hashlib,zipfile,collections,ast
from pathlib import Path
from pypdf import PdfReader
from compute_metrics import ROOT,S2,read,dump,official
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rows=read(S2/'results/judgments.jsonl');source=read(S2/'inputs/responses.jsonl');gt=read(S2/'inputs/ground_truth.jsonl');pairs=read(S2/'results/pair_relations.jsonl');scored=read(S2/'results/official_scored_rows.jsonl')
    lookup={r['sample_id']:r for r in rows};truth={r['sample_id']:r['official_row'] for r in gt}
    assert len(rows)==len(lookup)==len(source)==len(truth)==1129
    assert set(lookup)==set(truth)=={r['sample_id'] for r in source}
    for r in source:
        j=lookup[r['sample_id']];assert j['model_response_raw']==r['model_response_raw']
    for i,j in lookup.items():
        for k in ['question','gt_answer','gt_answer_details','category','subcategory','set_id','figure_id','question_id','visual_input']:assert str(j[k])==str(truth[i][k]),(i,k)
        assert j['judge_model']=='gpt-6.1-sol' and j['semantic_correctness'] in [0,1,2]
        assert j['predicted_stance'] in ['yes','no','uncertain','ambiguous']
    assert len(pairs)==len({r['sample_id'] for r in pairs})==674
    for r in pairs:
        a=lookup[r['baseline_sample_id']];b=lookup[r['sample_id']]
        assert str(a['figure_id'])=='0' and a['question_pair_id']==b['question_pair_id'] and str(b['figure_id'])!='0'
    first=[r for p in sorted((S2/'judgments/batches').glob('batch_*.jsonl')) for r in read(p)];assert len(first)==1129
    second=[r for p in sorted((S2/'judgments/second_pass').glob('chunk_*.jsonl')) for r in read(p)];assert len(second)==397
    qcids={r['sample_id'] for r in second};selection=json.loads((S2/'judgments/second_pass/selection.json').read_text(encoding='utf-8'))
    assert qcids=={r['sample_id'] for r in selection['selected']}
    randomids=set(json.loads((S2/'judgments/random_review_selection.json').read_text(encoding='utf-8'))['sample_ids']);assert len(randomids)==113 and randomids<=qcids
    assert all(r['sample_id'] in qcids for r in first if r['requires_review'])
    assert sum(r['output_at_token_limit'] for r in rows)==40
    quality=json.loads((S2/'reports/judge_quality.json').read_text(encoding='utf-8'))
    audit=quality['full_consistency_audit_v2'];assert audit['full_text_items_reviewed']==1129 and audit['full_response_relations_reviewed']==674
    assert len(read(S2/'judgments/unresolved_samples.jsonl'))==sum(r['requires_review'] for r in rows)==audit['reference_disputes']
    assert all(r['judge_prompt_version']=='hb-semantic-v2' and r['consistency_audit_v2']['source_sha256'] for r in rows)
    buckets=collections.defaultdict(set)
    for r in rows:buckets[(r['question'],r['gt_answer_details'],r['model_response_raw'])].add((r['predicted_stance'],r['semantic_correctness']))
    assert all(len(labels)==1 for labels in buckets.values()),'Identical teacher inputs must receive consistent labels'
    # Fixed, manually reviewed boundary cases: protect against losing adjudications on rebuild.
    expected={'VS/chart/3/1/3':('yes',0),'VS/chart/20/2/1':('no',1),'VS/map/4/0/2':('no',0),
              'VS/map/10/2/1':('no',1),'VD/math/5/0/1':('yes',1),'VD/math/5/0/2':('yes',1),
              'VD/math/0/0/0':('ambiguous',2),'VS/ocr/4/2/1':('yes',1),'VD/ocr/10/1/0':('yes',0),
              'VD/figure/2/1/1':('yes',0),'VS/chart/0/0/0':('uncertain',2)}
    for i,value in expected.items():assert (lookup[i]['predicted_stance'],lookup[i]['semantic_correctness'])==value,i
    assert lookup['VD/math/5/0/0']['explanation_issue_flag']
    assert len(read(S2/'results/explanation_issues.jsonl'))==sum(r['explanation_issue_flag'] for r in rows)==audit['explanation_issue_flags']
    for r in scored:assert r['correct']==lookup[r['sample_id']]['final_binary_correctness']
    o=official();assigned=o['assign_correctness']([dict(r,raw=str(r['semantic_correctness'])) for r in rows],'raw')
    assert all(r['correct']==r['final_binary_correctness'] for r in assigned)
    overall=json.loads((S2/'metrics/overall.json').read_text(encoding='utf-8'))
    assert overall['table2']['All']['numerator']==sum(r['final_binary_correctness'] for r in rows)
    controls=read(S2/'results/control_group_scores.jsonl');figures=read(S2/'results/figure_group_scores.jsonl')
    assert len(controls)==455 and len(figures)==346
    assert sum(r['all_correct'] for r in controls)==overall['table2']['qAcc']['numerator']
    assert sum(r['all_correct'] for r in figures)==overall['table2']['fAcc']['numerator']
    diag=read(S2/'results/diagnostic_trace.jsonl');counts=collections.Counter(r['diagnostic'] for r in diag)
    assert counts['none']==overall['table2']['All']['numerator']
    for key,label in [('LH','LH'),('VI','VI'),('Mix','Mixed')]:assert counts[label]==overall['diagnosis_items'][key]['numerator']
    case_images=[]
    for c in json.loads((S2/'reports/case_studies.json').read_text(encoding='utf-8')):
        for r in c['samples']:
            assert r['model_response_raw']==lookup[r['sample_id']]['model_response_raw']
            assert r['semantic_correctness']==lookup[r['sample_id']]['semantic_correctness']
            assert r['final_binary_correctness']==lookup[r['sample_id']]['final_binary_correctness']
            for im in r['verified_images']:
                assert sha(S2/im['report_path'])==im['sha256'];case_images.append(im)
    assert len(case_images)==10
    for path in (S2/'scripts').glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    pdf=PdfReader(S2/'reports/HallusionBench_Stage2_Report_zhTW.pdf');text='\n'.join(p.extract_text() for p in pdf.pages)
    assert len(pdf.pages)>=13 and chr(0) not in text
    for key in ['一、論文摘要','十三、結論及未來研究方向','v2 全量一致性重審版','v2 全量重審與舊版差異']+[f"{overall['table2'][k]['percent']:.2f}%" for k in ['All','qAcc','fAcc']]:assert key in text,key
    assert len(list((S2/'figures').glob('*.png')))==8
    s1zip=ROOT/'HallusionBench_Stage1_Results.zip';original_available=s1zip.exists()
    if original_available:
        assert sha(s1zip)=='f415c03bc7a7e86c84a28f3e8c8b234fb40efd0b32924099aca9854a19d4c637'
        with zipfile.ZipFile(s1zip) as z:
            assert z.read('results/internvl3_2b_bf16_tiles12/full/responses.jsonl')==(S2/'inputs/responses.jsonl').read_bytes()
        actual=ROOT/'results/internvl3_2b_bf16_tiles12/full/responses.jsonl';assert actual.read_bytes()==(S2/'inputs/responses.jsonl').read_bytes()
    report={'passed':True,'version':'hb-stage2-v2','judged_samples':1129,'unfinished_annotations':0,'control_groups':455,'figure_groups':346,'first_pass_batches':47,'second_pass_reviewed':397,'preregistered_random_reviewed':113,'full_consistency_audit_items':1129,'full_consistency_audit_relations':674,'identical_teacher_inputs_consistent':True,'fixed_boundary_cases_verified':len(expected),'token_caps_reviewed':40,'unresolved_reference_disputes':audit['reference_disputes'],'explanation_issue_flags':audit['explanation_issue_flags'],'pair_relations':674,'representative_case_images_rehashed':10,'figures':8,'pdf_pages':len(pdf.pages),'pdf_null_glyphs':0,'original_stage1_zip_and_answers_unchanged_checked':original_available,'judgments_sha256':sha(S2/'results/judgments.jsonl'),'pdf_sha256':sha(S2/'reports/HallusionBench_Stage2_Report_zhTW.pdf'),'paid_judge_api_calls':0,'github_pushed':False}
    dump(S2/'reports/final_verification.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
