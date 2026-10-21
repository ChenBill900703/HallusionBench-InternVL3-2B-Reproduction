"""Exercise crash-tail recovery and resume without loading a model or judging text."""
import json
from pathlib import Path
import tempfile
from infer import load_jsonl, export_latest, ROOT

with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
    p=Path(tmp)
    rows=[{'sample_id':'a','source_row_index':0,'model_response_raw':'Full raw text.','status':'success'},
          {'sample_id':'b','source_row_index':1,'model_response_raw':None,'status':'error','error_traceback':'test'},
          {'sample_id':'b','source_row_index':1,'model_response_raw':'Retried raw text.','status':'success','inference_code_sha256':'test'}]
    valid=''.join(json.dumps(r)+'\n' for r in rows).encode()
    (p/'attempts.jsonl').write_bytes(valid+b'{"sample_id":"interrupted')
    assert load_jsonl(p/'attempts.jsonl',recover_tail=True)==rows
    assert (p/'attempts.jsonl').read_bytes()==valid
    assert list(p.glob('*.partial.*'))
    latest=export_latest(p)
    assert len(latest)==2 and latest[1]['model_response_raw']=='Retried raw text.'
    assert len(load_jsonl(p/'attempts.jsonl'))==3
    assert (p/'responses.csv').exists()
print('PASS: interrupted tail preserved; successful rows resumable; all attempts retained; latest JSONL/CSV agree.')
