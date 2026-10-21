"""Verify official weight SHA-256 and snapshot source files for reproducibility."""
import hashlib
import json
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
name='OpenGVLab/InternVL3-2B'
catalog=json.loads((root/'reports/model_catalog.json').read_text(encoding='utf-8'))[name]
model=root/'models/internvl3_2b'
out=[]
runtime=root/'reports/model_runtime_source'
runtime.mkdir(parents=True,exist_ok=True)
for entry in catalog['siblings']:
    filename=entry['rfilename']
    path=model/filename
    if not path.is_file(): continue
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    row={'filename':filename,'bytes':path.stat().st_size,'sha256':h.hexdigest()}
    if entry.get('size') is not None: assert row['bytes']==entry['size'],filename
    expected=entry.get('lfs',{}).get('sha256')
    if expected: assert row['sha256']==expected,filename
    row['official_lfs_sha256']=expected
    out.append(row)
    if path.suffix in ['.py','.json'] and filename not in ['tokenizer.json','vocab.json','added_tokens.json']:
        shutil.copy2(path,runtime/filename)
record={'model':name,'revision':catalog['sha'],'files':out,'official_weight_sha_verified':all(r['official_lfs_sha256']==r['sha256'] for r in out if r['filename'].endswith('.safetensors'))}
(root/'reports/model_verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
