"""Extract the deliverable into a fresh directory and rebuild it without models or API."""
import argparse,hashlib,json,subprocess,sys,uuid,zipfile
from pathlib import Path,PurePosixPath
from pypdf import PdfReader
from compute_metrics import ROOT,S2,dump
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(write_report=True):
    archive=ROOT/'HallusionBench_Stage2_Results.zip'
    base=ROOT/'tmp';base.mkdir(exist_ok=True)
    dest=base/('stage2-v2-reproduction-'+uuid.uuid4().hex[:10]);dest.mkdir()
    assert dest.resolve().is_relative_to(base.resolve())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(n.startswith('stage2/') and not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in z.namelist())
        z.extractall(dest)
        inventory=json.loads(z.read('stage2/PACKAGE_MANIFEST.json'))['files']
        assert all(digest(dest/f['path'])==f['sha256'] for f in inventory)
    assert not (dest/'models').exists() and not (dest/'.venv').exists()
    steps=[['stage2/scripts/finalize_judgments.py'],['-m','unittest','discover','-s','stage2/scripts','-p','test_metrics.py','-v'],
           ['stage2/scripts/compute_metrics.py'],['stage2/scripts/build_figures.py'],['stage2/scripts/build_report.py'],
           ['stage2/scripts/write_delivery_notes.py'],['stage2/scripts/verify_final.py']]
    logs=[]
    for args in steps:
        run=subprocess.run([sys.executable,'-X','utf8',*args],cwd=dest,text=True,encoding='utf-8',capture_output=True)
        logs.append({'step':args,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        assert run.returncode==0,(args,run.stdout,run.stderr)
    paths=['results/judgments.jsonl','results/pair_relations.jsonl','results/official_scored_rows.jsonl','results/diagnostic_trace.jsonl',
           'results/control_group_scores.jsonl','results/figure_group_scores.jsonl','results/explanation_issues.jsonl',
           'metrics/overall.json','metrics/VD.json','metrics/VS.json','metrics/sensitivity.json','metrics/judge_effects.json',
           'metrics/table2_measured_counts.csv','metrics/table3_measured_counts.csv','metrics/comparison_tables.json',
           'reports/judge_quality.json','reports/consistency_audit_v2.json','reports/HallusionBench_Stage2_Report_zhTW.md','reports/report_content.json','README.md']
    paths += [p.relative_to(S2).as_posix() for p in sorted((S2/'figures').glob('*.png'))]
    verified=[]
    for relative in paths:
        current=S2/relative;rebuilt=dest/'stage2'/relative
        assert digest(current)==digest(rebuilt),relative
        verified.append({'path':'stage2/'+relative,'sha256':digest(current)})
    original=PdfReader(S2/'reports/HallusionBench_Stage2_Report_zhTW.pdf')
    regenerated=PdfReader(dest/'stage2/reports/HallusionBench_Stage2_Report_zhTW.pdf')
    assert len(original.pages)==len(regenerated.pages)
    assert [p.extract_text() for p in original.pages]==[p.extract_text() for p in regenerated.pages]
    report={'passed':True,'version':'hb-stage2-v2','archive':archive.name,'fresh_extraction':dest.relative_to(ROOT).as_posix(),
            'manifest_payload_files_rehashed':len(inventory),'reproduction_steps':len(steps),'all_steps_passed':True,
            'identical_recomputed_files':len(verified),'verified_files':verified,'regenerated_pdf_pages':len(regenerated.pages),
            'regenerated_pdf_page_text_identical':True,'model_weights_present':False,'GPU_inference_performed':False,'judge_api_calls':0,
            'independent_human_validation':False,'note':'Byte-identical saved-label reconstruction and calculations; not a new semantic annotation accuracy test. PDF metadata timestamps may differ.'}
    logpath=S2/'logs';logpath.mkdir(exist_ok=True)
    (logpath/'reproduction_v2.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2),encoding='utf-8')
    if write_report:dump(S2/'reports/reproduction_check.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='verified_files'},ensure_ascii=False,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args();main(not args.check_only)
