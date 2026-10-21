"""Verify source metadata and construct separate inference and ground-truth manifests."""
import collections
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
KEY_FIELDS = ('category', 'subcategory', 'set_id', 'figure_id', 'question_id')

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def key(r):
    return '/'.join(str(r[k]) for k in KEY_FIELDS)

def write_jsonl(path, rows):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

def main():
    from PIL import Image
    source = ROOT / 'upstream/HallusionBench/HallusionBench.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    assert len(data) == 1129
    assert len({key(r) for r in data}) == len(data), 'Duplicate official composite key'
    source_marker = ROOT/'data/image_source.json'
    existing_report = ROOT/'reports/dataset_integrity.json'
    mirror_report = json.loads(source_marker.read_text(encoding='utf-8')) if source_marker.exists() else (
        json.loads(existing_report.read_text(encoding='utf-8'))['image_mirror'] if existing_report.exists() else {'used':False})
    all_images_present = all((ROOT/'data'/r['filename'].removeprefix('./')).is_file() for r in data if str(r['visual_input'])!='0')
    if not all_images_present:
        import pyarrow.parquet as pq
        mirror = []
        for path in sorted((ROOT / 'data/mirror/data').glob('*.parquet')):
            mirror.extend(pq.read_table(path).to_pylist())
        assert len(mirror) == len(data), ('Mirror length', len(mirror))
        by_id = {key(r): r for r in mirror}
        assert len(by_id) == len(data)
        mismatches = []
        for r in data:
            m = by_id[key(r)]
            for field in r:
                if field == 'filename':
                    continue
                if m.get(field) != r[field]:
                    mismatches.append([key(r), field, r[field], m.get(field)])
        assert not mismatches, ('Mirror metadata differs from official', mismatches[:10])
        written = {}
        for r in data:
            if str(r['visual_input']) == '0':
                assert by_id[key(r)].get('image') is None
                continue
            raw = by_id[key(r)]['image']['bytes']
            dest = ROOT / 'data' / r['filename'].removeprefix('./')
            assert dest.resolve().is_relative_to(ROOT / 'data')
            digest = hashlib.sha256(raw).hexdigest()
            if dest in written:
                assert written[dest] == digest, 'Inconsistent image bytes for same filename'
            else:
                Image.open(io.BytesIO(raw)).verify()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
                written[dest] = digest
        mirror_report = {'used': True, 'metadata_rows_compared': len(data),
                         'metadata_mismatches': 0, 'unique_images_restored': len(written),
                         'source': json.loads((ROOT / 'reports/image_mirror_source.json').read_text(encoding='utf-8'))['id'],
                         'revision': json.loads((ROOT / 'reports/image_mirror_source.json').read_text(encoding='utf-8'))['sha'],
                         'original_drive_http_status': 404,
                         'limitation': 'Metadata matches official JSON. Original Drive image bytes unavailable; byte identity with original archive cannot be independently proven.'}
    source_marker.write_text(json.dumps(mirror_report,indent=2),encoding='utf-8')
    manifest = []
    ground = []
    image_rows = {}
    controls = collections.defaultdict(list)
    figures = collections.defaultdict(list)
    for idx, r in enumerate(data):
        sid = key(r)
        pair = '_'.join(str(r[k]) for k in ('category','subcategory','set_id','question_id'))
        figure = '_'.join(str(r[k]) for k in ('category','subcategory','set_id','figure_id'))
        no_visual = str(r['visual_input']) == '0'
        image_type = {'0':'no_visual', '1':'original', '2':'edited'}[str(r['visual_input'])]
        paths = [] if no_visual else [('data/' + r['filename'].removeprefix('./'))]
        for path in paths:
            p = ROOT / path
            if path not in image_rows:
                with Image.open(p) as im:
                    im.verify()
                with Image.open(p) as im:
                    image_rows[path] = {'path': path, 'sha256':sha256(p), 'width':im.width, 'height':im.height, 'format':im.format,
                                        'storage': 'official_composite_png' if r['subcategory']=='video' else 'official_single_png'}
        safe_meta = {k:v for k,v in r.items() if not k.startswith('gt_')}
        item = {'sample_id':sid, 'sample_id_origin':'derived_from_official_composite_key', 'source_row_index':idx,
                'question':r['question'], 'original_question_metadata':safe_meta,
                'image_path':paths[0] if paths else None, 'image_paths':paths,
                'image_sha256':[image_rows[p]['sha256'] for p in paths],
                'image_type':image_type, 'category':r['category'], 'subcategory':r['subcategory'],
                'paper_subcategory':'poster' if (r['category'],r['subcategory'])==('VD','ocr') else r['subcategory'],
                'question_pair_id':pair, 'figure_id':r['figure_id'], 'set_id':r['set_id'], 'question_id':r['question_id'],
                'figure_group_key': None if no_visual else figure, 'visual_input':r['visual_input']}
        manifest.append(item)
        ground.append({'sample_id':sid, 'question_pair_id':pair, 'figure_group_key':item['figure_group_key'],
                       'official_row':r, 'source_row_index':idx})
        controls[pair].append(sid)
        if not no_visual:
            figures[figure].append(sid)
    report = {'question_count':len(data), 'unique_images':len(image_rows), 'question_control_groups':len(controls),
              'image_condition_question_counts':dict(collections.Counter(x['image_type'] for x in manifest)),
              'unique_image_conditions':dict(collections.Counter(next(x['image_type'] for x in manifest if x['image_path']==p) for p in image_rows)),
              'category_subcategory_conditions':dict(collections.Counter(f"{x['category']}/{x['subcategory']}/{x['image_type']}" for x in manifest)),
              'missing_images':[], 'duplicate_sample_ids':[], 'image_mirror':mirror_report,
              'dataset_json_sha256':sha256(source), 'upstream_commit':subprocess.check_output(['git','-C',str(ROOT/'upstream/HallusionBench'),'rev-parse','HEAD'],text=True).strip(),
              'dataset_last_change_commit':'c226ce45c95eec2935b09789099409c682a6c05d',
              'id_policy':'sample_id is a derived composite key; question_pair_id follows official utils.py, not a new official ID.',
              'video_policy':'Official filenames reference precomposed consecutive-image PNGs. Preserve whole PNG and frame layout/order; no frame resampling or reordering.',
              'label_note':'Official VD/ocr corresponds to Poster in paper. Original metadata retained.'}
    assert (len(image_rows),len(controls)) == (346,455)
    assert report['image_condition_question_counts'] == {'no_visual':178,'original':447,'edited':504}
    assert report['unique_image_conditions'] == {'original':165,'edited':181}
    (ROOT/'data/manifests').mkdir(parents=True,exist_ok=True)
    write_jsonl(ROOT/'data/manifests/inference.jsonl',manifest)
    write_jsonl(ROOT/'data/manifests/ground_truth.jsonl',ground)
    write_jsonl(ROOT/'data/manifests/images.jsonl',image_rows.values())
    (ROOT/'data/manifests/control_groups.json').write_text(json.dumps({'question_pairs':controls,'figures':figures},indent=2),encoding='utf-8')
    # Recursively forbid answer fields in all inference metadata.
    def check_safe(value):
        if isinstance(value,dict):
            assert not any(k.startswith('gt_') or k in {'correct','answer','gt_answer'} for k in value)
            for v in value.values(): check_safe(v)
        elif isinstance(value,list):
            for v in value: check_safe(v)
    check_safe(manifest)
    (ROOT/'reports/dataset_integrity.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
