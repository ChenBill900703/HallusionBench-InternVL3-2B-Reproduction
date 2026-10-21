"""Download only official, revision-pinned assets. No inference or evaluation."""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('HF_HOME', str(ROOT / '.hf'))
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '120')
os.environ.setdefault('HF_HUB_ETAG_TIMEOUT', '60')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('asset', choices=['images', 'internvl3_2b'])
    args = p.parse_args()
    if args.asset == 'images':
        import gdown
        import zipfile
        target = ROOT / 'data/hallusion_bench.zip'
        if not target.exists() or not zipfile.is_zipfile(target):
            try:
                gdown.download(id='1eeO1i0G9BSZTE1yd5XeFwmrbe1hwyf_0', output=str(target), quiet=False)
                if not target.exists() or not zipfile.is_zipfile(target):
                    raise ValueError('Official source did not return a ZIP archive')
            except Exception as exc:
                print(f'Official image link failed: {exc}. Using pinned research mirror.',flush=True)
                from huggingface_hub import snapshot_download
                import urllib.request
                name='lmms-lab-encoder/HallusionBench'
                recorded=ROOT/'reports/image_mirror_source.json'
                meta=json.loads(recorded.read_text(encoding='utf-8')) if recorded.exists() else json.load(urllib.request.urlopen('https://huggingface.co/api/datasets/'+name))
                recorded.write_text(json.dumps(meta,indent=2),encoding='utf-8')
                snapshot_download(name,repo_type='dataset',revision=meta['sha'],local_dir=ROOT/'data/mirror',max_workers=2)
                return
        with zipfile.ZipFile(target) as z:
            for name in z.namelist():
                dest = (ROOT / 'data' / name).resolve()
                if not dest.is_relative_to(ROOT / 'data'):
                    raise ValueError('Unsafe archive member: ' + name)
            bad = z.testzip()
            if bad:
                raise ValueError('Corrupt member: ' + bad)
            z.extractall(ROOT / 'data')
        # Published JSON omits the outer hallusion_bench/ archive directory.
        import shutil
        for category in ['VD','VS']:
            src=ROOT/'data/hallusion_bench'/category
            if src.is_dir(): shutil.copytree(src,ROOT/'data'/category,dirs_exist_ok=True)
        print('Official image archive verified and extracted.', flush=True)
    from huggingface_hub import snapshot_download
    catalog = json.loads((ROOT / 'reports/model_catalog.json').read_text(encoding='utf-8'))
    names = {'internvl3_2b':'OpenGVLab/InternVL3-2B'}
    for key, name in names.items():
        if args.asset != key:
            continue
        rev = catalog[name]['sha']
        print(f'Downloading {name} @ {rev}', flush=True)
        snapshot_download(name, revision=rev, local_dir=ROOT / 'models' / key,
                          allow_patterns=['*.json', '*.py', '*.txt', '*.model', '*.safetensors', 'README.md', '*LICENSE*'],
                          max_workers=3)
        (ROOT / 'models' / key / 'SOURCE_REVISION.json').write_text(json.dumps({'model':name, 'revision':rev}, indent=2),encoding='utf-8')
        print(f'Completed {name}', flush=True)

if __name__ == '__main__':
    main()
