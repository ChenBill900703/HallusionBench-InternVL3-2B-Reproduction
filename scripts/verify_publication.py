"""Read-only validation of this publication; never judges or edits labels."""
import collections, hashlib, importlib.util, json, re, sys, unicodedata
from pathlib import Path
from urllib.parse import unquote
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def slug(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text).replace('**','').replace('`','').lower()
    text = ''.join(c for c in text if c.isalnum() or c in ' _-' or unicodedata.category(c).startswith('M'))
    return text.replace(' ', '-')
def anchors(path):
    found = set(); counts = collections.Counter()
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', path.read_text(encoding='utf-8'), re.M):
        key = slug(title); n = counts[key]; counts[key] += 1
        found.add(key if n == 0 else key+'-'+str(n))
    return found
def check_links():
    bad = []
    for p in sorted(ROOT.rglob('*.md')):
        if '.git' in p.parts: continue
        content = re.sub(r'```.*?```', '', p.read_text(encoding='utf-8'), flags=re.S)
        for url in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', content):
            url = url.strip().strip('<>')
            if re.match(r'^(https?://|mailto:|data:)', url): continue
            rel, _, anchor = unquote(url).partition('#')
            target = (p.parent/rel).resolve() if rel else p
            if not target.is_relative_to(ROOT): bad.append((str(p.relative_to(ROOT)),url,'outside repository')); continue
            if not target.exists(): bad.append((str(p.relative_to(ROOT)),url,'missing target')); continue
            if anchor and target.suffix == '.md' and anchor not in anchors(target):
                bad.append((str(p.relative_to(ROOT)),url,'missing heading'))
    return bad
def main():
    frozen=load(ROOT/'reports/stage3/immutable_inputs.json')
    for rel, expected in frozen.items(): assert sha(ROOT/rel)==expected, ('Immutable input differs',rel)
    raw=rows(ROOT/'results/internvl3_2b_bf16_tiles12/full/responses.jsonl')
    gt=rows(ROOT/'data/manifests/ground_truth.jsonl')
    labels=rows(ROOT/'stage2/results/judgments.jsonl')
    pairs=rows(ROOT/'stage2/results/pair_relations.jsonl')
    rmap={r['sample_id']:r for r in raw}; gmap={r['sample_id']:r['official_row'] for r in gt}
    assert len(raw)==len(gt)==len(labels)==len(rmap)==len(gmap)==1129
    assert set(rmap)==set(gmap)=={r['sample_id'] for r in labels}
    for r in labels:
        assert r['model_response_raw']==rmap[r['sample_id']]['model_response_raw']
        for k in ['question','gt_answer','gt_answer_details']: assert r[k]==gmap[r['sample_id']][k]
    assert sha(ROOT/'stage2/inputs/responses.jsonl')==frozen['results/internvl3_2b_bf16_tiles12/full/responses.jsonl']
    assert sha(ROOT/'stage2/inputs/ground_truth.jsonl')==frozen['data/manifests/ground_truth.jsonl']
    assert collections.Counter(r['semantic_correctness'] for r in labels)=={1:554,0:412,2:163}
    spec=importlib.util.spec_from_file_location('hb_compute',ROOT/'stage2/scripts/compute_metrics.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    adapted=mod.adapt(labels,pairs); actual=mod.summarize(adapted)
    saved=load(ROOT/'stage2/metrics/overall.json')
    assert actual==saved, 'Computed metrics differ from saved metrics'
    expected={'qAcc':(102,455),'fAcc':(100,346),'Easy':(251,455),'Hard':(193,430),'All':(617,1129)}
    for key, value in expected.items():
        assert (actual['table2'][key]['numerator'],actual['table2'][key]['denominator'])==value
    assert [actual['consistency'][k]['numerator'] for k in ['correct','inconsistent','wrong']]==[100,177,69]
    assert [actual['diagnosis_items'][k]['numerator'] for k in ['LH','VI','Mix']]==[112,279,121]
    assert abs(actual['bias']['official_pct_diff']['fraction']-168/1129)<1e-12
    assert abs(actual['bias']['official_fp_ratio']['fraction']-340/512)<1e-12
    assert len(pairs)==674 and collections.Counter(r['relation'] for r in pairs)=={'same':287,'different':232,'uncertain':155}
    assert len(list((ROOT/'stage2/judgments/batches').glob('batch_*.jsonl')))==47
    assert sum(len(rows(p)) for p in (ROOT/'stage2/judgments/second_pass').glob('chunk_*.jsonl'))==397
    assert sum(len(rows(p)) for p in (ROOT/'stage2/judgments/consistency_v2').glob('batch_*.jsonl'))==1129
    assert len(rows(ROOT/'stage2/judgments/unresolved_samples.jsonl'))==32
    assert len(rows(ROOT/'stage2/results/explanation_issues.jsonl'))==87
    assert len(load(ROOT/'stage2/reports/case_studies.json'))==6
    assert len(list((ROOT/'stage2/figures').glob('*.png')))==8
    assert not list((ROOT/'stage2/figures').glob('cases/*.png'))
    assert not (ROOT/'data/VD').exists() and not (ROOT/'data/VS').exists()
    image_files=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*.png') if '.git' not in p.parts]
    assert len(image_files)==8
    from pypdf import PdfReader
    pdf=ROOT/'reports/HallusionBench_Research_Report_zhTW.pdf'
    reader=PdfReader(pdf); assert len(reader.pages)>=10
    assert '54.65' in ''.join(p.extract_text() or '' for p in reader.pages)
    assert [p for p in ROOT.rglob('*.pdf') if '.git' not in p.parts]==[pdf]
    bad=check_links()
    if bad:
        print(json.dumps({'broken_links':bad},ensure_ascii=False,indent=2)); raise AssertionError('Fix Markdown links')
    # Match credential values, not harmless words such as api_key in source.
    patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{40,}',r'sk-(?:proj-)?[A-Za-z0-9_-]{40,}',r'hf_[A-Za-z0-9]{30,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    secret_paths=[]; large=[]
    files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts]
    for p in files:
        if p.stat().st_size>=100_000_000: large.append(p.relative_to(ROOT).as_posix())
        if p.suffix.lower() in ['.png','.pdf']: continue
        s=p.read_text(encoding='utf-8-sig',errors='replace')
        if any(re.search(pattern,s) for pattern in patterns): secret_paths.append(p.relative_to(ROOT).as_posix())
    assert not secret_paths, ('Credential-like values found; values withheld',secret_paths)
    assert not large, ('GitHub size limit exceeded',large)
    manifest=ROOT/'reports/publication_manifest.json'
    if manifest.exists():
        m=load(manifest)
        expected_files={r['path'] for r in m['files']}
        actual_files={p.relative_to(ROOT).as_posix() for p in files}-{manifest.relative_to(ROOT).as_posix()}
        assert expected_files==actual_files, ('Publication file set differs', sorted(actual_files^expected_files))
        for item in m['files']: assert sha(ROOT/item['path'])==item['sha256'], ('Published payload changed',item['path'])
    print(json.dumps({'passed':True,'responses':1129,'question_groups':455,'figure_groups':346,'metrics_counts':expected,'charts':8,'pdf_pages':len(reader.pages),'markdown_links':'passed','credential_value_scan':'passed','immutable_inputs':'unchanged','manifest_checked':manifest.exists(),'GPU_inference':False,'new_semantic_judging':False},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
