"""Inventory the publication after preparing documents; excludes this manifest itself."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=ROOT/'reports/publication_manifest.json'
    excluded_dirs={'.git','__pycache__','.venv','.venv-eval','.hf','.bootstrap','tmp','models','upstream'}
    paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and not (set(p.relative_to(ROOT).parts)&excluded_dirs) and p!=target)
    assert all(p.stat().st_size<100_000_000 for p in paths)
    files=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    audit=json.loads((ROOT/'reports/stage3/source_audit.json').read_text(encoding='utf-8'))
    source={}
    for path in ['reports/stage3/stage1_PACKAGE_MANIFEST.json','stage2/PACKAGE_MANIFEST.json']:
        values=json.loads((ROOT/path).read_text(encoding='utf-8'));values=values['files'] if isinstance(values,dict) else values
        source.update({r['path']:r['sha256'] for r in values})
    adapted=[{'path':f['path'],'source_archive_sha256':source[f['path']],'publication_sha256':f['sha256']} for f in files if f['path'] in source and source[f['path']]!=f['sha256']]
    body={'version':'stage3-publication-v1','inventory_scope':'All distributed files except this manifest; Git metadata and generated Python cache excluded.',
          'payload_file_count':len(files),'tracked_file_count_including_manifest':len(files)+1,
          'total_payload_bytes':sum(r['bytes'] for r in files),
          'original_archives':audit['archives'],'source_images_or_embedded_image_documents_excluded':audit['excluded'],
          'privacy_redactions':audit['privacy_redactions'],'adapted_publication_files':adapted,
          'adaptation_note':'Publication documentation, ignore rules, citation and image-safe report links updated; download fallback checks invalid ZIP. Source archives unchanged. See immutable input SHA-256 for original answers, GT and final labels.',
          'immutable_inputs':json.loads((ROOT/'reports/stage3/immutable_inputs.json').read_text(encoding='utf-8')),
          'files':files}
    target.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'payload_files':len(files),'total_tracked_files':len(files)+1,'payload_bytes':body['total_payload_bytes'],'adapted_source_files':len(adapted)},ensure_ascii=False))
if __name__=='__main__':main()
