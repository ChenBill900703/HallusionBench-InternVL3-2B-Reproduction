"""Stage 1 only. This program reads no ground-truth manifest and performs no judging."""
import argparse
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('HF_HOME', str(ROOT / '.hf'))
os.environ.setdefault('HF_MODULES_CACHE', str(ROOT / '.hf/modules'))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
sys.stdout.reconfigure(encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_jsonl(path, recover_tail=False):
    if not path.exists(): return []
    raw = path.read_bytes()
    rows = []
    offset = 0
    for i, line in enumerate(raw.splitlines(keepends=True)):
        try:
            rows.append(json.loads(line))
        except (json.JSONDecodeError, UnicodeDecodeError):
            if recover_tail and offset + len(line) == len(raw) and not line.endswith(b'\n'):
                backup = path.with_suffix('.partial.' + str(time.time_ns()))
                backup.write_bytes(line)
                with open(path,'r+b') as f: f.truncate(offset)
                print(f'Recovered interrupted final JSONL line to {backup}',flush=True)
                break
            raise ValueError(f'Invalid JSONL {path}, line {i+1}')
        offset += len(line)
    return rows

def export_latest(outdir):
    latest = {}
    for row in load_jsonl(outdir/'attempts.jsonl'):
        latest[row['sample_id']] = row
    rows = sorted(latest.values(),key=lambda r:r['source_row_index'])
    tmp = outdir/'responses.jsonl.tmp'
    tmp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    tmp.replace(outdir/'responses.jsonl')
    if rows:
        with open(outdir/'responses.csv','w',encoding='utf-8-sig',newline='') as f:
            fields = list(dict.fromkeys(k for row in rows for k in row))
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in rows:
                w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    return rows

def tiles(image, max_num, image_size=448):
    # From OpenGVLab/InternVL3-2B's official model card, pinned in models/.
    width,height = image.size
    ratio = width / height
    ratios = set((i,j) for n in range(1,max_num+1) for i in range(1,n+1) for j in range(1,n+1) if 1 <= i*j <= max_num)
    best = (1,1)
    best_diff = float('inf')
    for target in sorted(ratios,key=lambda r:r[0]*r[1]):
        diff = abs(ratio-target[0]/target[1])
        if diff < best_diff or (diff == best_diff and width*height > 0.5*image_size*image_size*target[0]*target[1]):
            best_diff,best = diff,target
    im = image.resize((image_size*best[0],image_size*best[1]))
    result = [im.crop(((i%best[0])*image_size,(i//best[0])*image_size,((i%best[0])+1)*image_size,((i//best[0])+1)*image_size)) for i in range(best[0]*best[1])]
    if len(result)>1: result.append(image.resize((image_size,image_size)))
    return result

class InternVL:
    def __init__(self,cfg):
        import torch
        import torchvision.transforms as T
        from torchvision.transforms.functional import InterpolationMode
        from transformers import AutoModel, AutoTokenizer
        self.cfg = cfg
        path = str(ROOT/cfg['local_model_path'])
        self.tokenizer = AutoTokenizer.from_pretrained(path,trust_remote_code=True,use_fast=False,local_files_only=True)
        self.model = AutoModel.from_pretrained(path,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True,
                                              trust_remote_code=True,use_flash_attn=False,local_files_only=True).eval().cuda()
        self.transform = T.Compose([T.Resize((448,448),interpolation=InterpolationMode.BICUBIC),T.ToTensor(),T.Normalize((.485,.456,.406),(.229,.224,.225))])
        original_generate = self.model.generate
        def capture(*args,**kwargs):
            self.input_token_ids = kwargs['input_ids'][0].detach().cpu().tolist()
            self.generated_ids = original_generate(*args,**kwargs)[0].detach().cpu().tolist()
            return torch.tensor([self.generated_ids],device=self.model.device)
        self.model.generate = capture

    def predict(self,sample,prompt):
        import torch
        from PIL import Image
        pixels=[]
        patches=[]
        original_sizes=[]
        for path in sample['image_paths']:
            with Image.open(ROOT/path) as im:
                im = im.convert('RGB')
                original_sizes.append(list(im.size))
                chunk = [self.transform(x) for x in tiles(im,self.cfg['max_dynamic_tiles'])]
                pixels.extend(chunk)
                patches.append(len(chunk))
        pv = torch.stack(pixels).to(device='cuda',dtype=torch.bfloat16) if pixels else None
        prefix = ''.join(('<image>\n' if len(patches)==1 else f'Image-{i+1}: <image>\n') for i in range(len(patches)))
        self.input_token_ids=[]
        self.generated_ids=[]
        with torch.inference_mode():
            response = self.model.chat(self.tokenizer,pv,prefix+prompt,dict(self.cfg['generation']),
                                       history=None,num_patches_list=patches or None)
        ids = self.generated_ids
        raw_decode = self.tokenizer.decode(ids,skip_special_tokens=False)
        return response, {'generated_token_ids':ids,'decoded_with_special_tokens':raw_decode,
                          'generated_tokens':len(ids),'input_tokens':len(self.input_token_ids),
                          'input_ids_sha256':hashlib.sha256(json.dumps(self.input_token_ids).encode()).hexdigest(),
                          'image_patch_counts':patches,'original_image_sizes':original_sizes,
                          'system_prompt':self.model.system_message,'image_prefix':prefix,
                          'output_at_token_limit':len(ids)>=self.cfg['generation']['max_new_tokens']}

class Qwen:
    def __init__(self,cfg):
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration, Qwen2_5_VLForConditionalGeneration, BitsAndBytesConfig
        self.cfg = cfg
        path = str(ROOT/cfg['local_model_path'])
        self.processor = AutoProcessor.from_pretrained(path,local_files_only=True,
                                                      min_pixels=cfg['min_pixels'],max_pixels=cfg['max_pixels'])
        cls = Qwen3VLForConditionalGeneration if cfg['backend']=='qwen3' else Qwen2_5_VLForConditionalGeneration
        kwargs = dict(torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa',local_files_only=True)
        if cfg.get('quantization') == 'bnb_nf4':
            kwargs['quantization_config'] = BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
                                                             bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16,
                                                             llm_int8_skip_modules=['visual'])
        self.model = cls.from_pretrained(path,**kwargs).eval()

    def predict(self,sample,prompt):
        import torch
        from PIL import Image
        images=[]
        for path in sample['image_paths']:
            with Image.open(ROOT/path) as im: images.append(im.convert('RGB'))
        messages = [{'role':'user','content':[{'type':'image'} for im in images]+[{'type':'text','text':prompt}]}]
        rendered = self.processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        kwargs = {'text':[rendered],'return_tensors':'pt','padding':True}
        if images: kwargs['images']=images
        inputs = self.processor(**kwargs).to('cuda')
        length = inputs['input_ids'].shape[1]
        grid = inputs['image_grid_thw'].cpu().tolist() if images else []
        with torch.inference_mode():
            out = self.model.generate(**inputs,**self.cfg['generation'])
        ids = out[0,length:].cpu().tolist()
        response = self.processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        return response, {'generated_token_ids':ids,'decoded_with_special_tokens':self.processor.tokenizer.decode(ids,skip_special_tokens=False),
                          'generated_tokens':len(ids),'input_tokens':length,'image_grid_thw':grid,
                          'input_ids_sha256':hashlib.sha256(json.dumps(inputs['input_ids'][0].cpu().tolist()).encode()).hexdigest(),
                          'rendered_chat_template':rendered,'original_image_sizes':[list(im.size) for im in images],
                          'output_at_token_limit':len(ids)>=self.cfg['generation']['max_new_tokens']}

def smoke_samples(samples):
    # Cover every category/subcategory/input condition plus largest source images.
    selected = {}
    seen = set()
    for r in samples:
        group = (r['category'],r['subcategory'],r['image_type'])
        if group not in seen:
            selected[r['sample_id']] = r
            seen.add(group)
    images = load_jsonl(ROOT/'data/manifests/images.jsonl')
    for image in sorted(images,key=lambda r:r['width']*r['height'],reverse=True)[:3]:
        r = next(r for r in samples if image['path'] in r['image_paths'])
        selected[r['sample_id']] = r
    return list(selected.values())

def main():
    import psutil
    import torch
    p = argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--smoke',action='store_true')
    p.add_argument('--limit',type=int)
    p.add_argument('--retry-failed',action='store_true')
    args = p.parse_args()
    cfg = json.loads((ROOT/args.config).read_text(encoding='utf-8'))
    config_hash = hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    code_hash = digest(Path(__file__))
    manifest = ROOT/'data/manifests/inference.jsonl'
    samples = load_jsonl(manifest)
    assert len({s['sample_id'] for s in samples}) == len(samples)
    if args.smoke: samples = smoke_samples(samples)
    if args.limit: samples = samples[:args.limit]
    outdir = ROOT/'results'/cfg['run_name']/('smoke' if args.smoke else 'full')
    outdir.mkdir(parents=True,exist_ok=True)
    lock = outdir/'run.lock'
    if lock.exists():
        pid = int(lock.read_text())
        if psutil.pid_exists(pid): raise RuntimeError(f'Run already locked by live PID {pid}')
        lock.unlink()
    fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode()); os.close(fd)
    model = None
    try:
        attempts = load_jsonl(outdir/'attempts.jsonl',recover_tail=True)
        latest = {r['sample_id']:r for r in attempts}
        for r in attempts:
            assert r['config_sha256']==config_hash, 'Configuration changed: use a new run_name'
            assert r['inference_manifest_sha256']==digest(manifest), 'Manifest changed: use a new run_name'
        todo = [r for r in samples if r['sample_id'] not in latest or (args.retry_failed and latest[r['sample_id']]['status']!='success')]
        if not todo:
            export_latest(outdir)
            print('All selected samples already completed; no model load needed.',flush=True)
            return
        assert torch.cuda.is_available(), 'CUDA unavailable'
        random.seed(cfg['seed']); torch.manual_seed(cfg['seed']); torch.cuda.manual_seed_all(cfg['seed'])
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        torch.backends.cudnn.benchmark=False
        torch.use_deterministic_algorithms(True,warn_only=True)
        torch.set_num_threads(8)
        started = datetime.now(timezone.utc).isoformat()
        torch.cuda.reset_peak_memory_stats()
        load_t0 = time.perf_counter()
        model = InternVL(cfg) if cfg['backend']=='internvl' else Qwen(cfg)
        torch.cuda.synchronize()
        env = {'started_utc':started,'model_load_seconds':time.perf_counter()-load_t0,'config':cfg,
               'config_sha256':config_hash,'inference_code_sha256':code_hash,'manifest_sha256':digest(manifest),'pid':os.getpid(),
               'torch':torch.__version__,'cuda_runtime':torch.version.cuda,'gpu':torch.cuda.get_device_name(),
               'gpu_total_bytes':torch.cuda.get_device_properties(0).total_memory,
               'load_peak_allocated_bytes':torch.cuda.max_memory_allocated(),
               'cpu':os.environ.get('PROCESSOR_IDENTIFIER'),'ram':psutil.virtual_memory()._asdict(),
               'selected_sample_count':len(samples),'pending_count_at_start':len(todo)}
        (outdir/f'run_{time.time_ns()}.json').write_text(json.dumps(env,indent=2),encoding='utf-8')
        print(json.dumps({'event':'model_loaded','run':cfg['run_name'],'pending':len(todo),'load_seconds':env['model_load_seconds'],'vram_bytes':env['load_peak_allocated_bytes']}),flush=True)
        with open(outdir/'attempts.jsonl','a',encoding='utf-8',newline='\n') as f:
            for n,sample in enumerate(todo):
                row = dict(sample)
                row.update({'model_name':cfg['model_name'],'model_version':cfg['revision'],'run_name':cfg['run_name'],
                            'config_sha256':config_hash,'inference_code_sha256':code_hash,'inference_manifest_sha256':env['manifest_sha256'],
                            'attempt':1+sum(r['sample_id']==sample['sample_id'] for r in attempts),
                            'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                            'inference_parameters':cfg,'prompt_text':cfg['prompt_template'].format(question=sample['question']),
                            'model_response_raw':None,'generation_details':None,'status':'error','error_message':None,'error_traceback':None,
                            'inference_time':None,'peak_vram_allocated_bytes':None,'peak_vram_reserved_bytes':None})
                torch.cuda.reset_peak_memory_stats()
                t0 = time.perf_counter()
                try:
                    response,details = model.predict(sample,row['prompt_text'])
                    torch.cuda.synchronize()
                    row['model_response_raw']=response
                    row['generation_details']=details
                    row['status']='success' if response.strip() else 'empty_response'
                    if row['status']=='empty_response': row['error_message']='Model returned empty assistant text; no answer inferred.'
                except Exception as exc:
                    row['error_message']=f'{type(exc).__name__}: {exc}'
                    row['error_traceback']=traceback.format_exc()
                    gc.collect(); torch.cuda.empty_cache()
                row['inference_time']=time.perf_counter()-t0
                row['peak_vram_allocated_bytes']=torch.cuda.max_memory_allocated()
                row['peak_vram_reserved_bytes']=torch.cuda.max_memory_reserved()
                f.write(json.dumps(row,ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
                print(json.dumps({'event':'sample','sample_id':sample['sample_id'],'status':row['status'],
                                  'seconds':round(row['inference_time'],3),'processed':n+1,'remaining':len(todo)-n-1,
                                  'error':row['error_message']},ensure_ascii=False),flush=True)
                if n % 25 == 0: export_latest(outdir)
                # Stop quickly if a systematic error occurs, retaining all failures.
                if n>=2 and all(r.get('status')!='success' for r in attempts[-2:]) and row['status']!='success':
                    raise RuntimeError('Three consecutive inference failures. Inspect recorded errors before retry.')
                attempts.append(row)
        export_latest(outdir)
    finally:
        if (outdir/'attempts.jsonl').exists(): export_latest(outdir)
        del model
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        lock.unlink(missing_ok=True)
        print(json.dumps({'event':'process_cleanup','allocated':torch.cuda.memory_allocated() if torch.cuda.is_available() else None}),flush=True)

if __name__=='__main__':
    main()
