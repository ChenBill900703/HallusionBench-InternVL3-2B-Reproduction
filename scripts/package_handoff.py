"""Package single-model raw outputs and batchable stage-2 inputs. No grading."""
import collections
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from datetime import datetime,timezone
from verify_results import verify,read,sha,ROOT

RUN='internvl3_2b_bf16_tiles12'
def main():
    integrity=verify(RUN,strict=True)
    out=ROOT/'handoff'
    ground={r['sample_id']:r for r in read(ROOT/'data/manifests/ground_truth.jsonl')}
    responses=read(ROOT/'results'/RUN/'full/responses.jsonl')
    grouped=collections.defaultdict(list)
    for r in responses:
        gt=ground[r['sample_id']]['official_row']
        grouped[r['question_pair_id']].append({'sample_id':r['sample_id'],'question':r['question'],
                    'category':r['category'],'subcategory':r['subcategory'],'visual_input':r['visual_input'],
                    'set_id':r['set_id'],'figure_id':r['figure_id'],'question_id':r['question_id'],
                    'figure_group_key':r['figure_group_key'],'image_type':r['image_type'],'image_paths':r['image_paths'],
                    'gt_answer':gt['gt_answer'],'gt_answer_details':gt['gt_answer_details'],
                    'model_response_raw':r['model_response_raw'],'status':r['status'],
                    'error_message':r['error_message'],'output_at_token_limit':r['generation_details']['output_at_token_limit']})
    batches=out/'stage2_batches'
    batches.mkdir(exist_ok=True)
    batch=[]; n=0; count=0; batch_index=[]
    def save(items,index):
        path=batches/f'batch_{index:03d}.jsonl'
        path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items),encoding='utf-8')
        batch_index.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'question_groups':len(items),
                            'sample_count':sum(len(x['samples']) for x in items),'sha256':sha(path)})
    for pair,rows in grouped.items():
        if count+len(rows)>25 and batch:
            n+=1; save(batch,n); batch=[]; count=0
        batch.append({'model_name':'OpenGVLab/InternVL3-2B','run_name':RUN,'question_pair_id':pair,'samples':rows})
        count+=len(rows)
    if batch: n+=1; save(batch,n)
    (out/'stage2_batches/index.json').write_text(json.dumps(batch_index,indent=2),encoding='utf-8')
    assert sum(b['sample_count'] for b in batch_index)==1129
    assert sum(b['question_groups'] for b in batch_index)==455
    # The official repo grants BSD-3-Clause redistribution of its source/data JSON.
    upstream=out/'upstream_reference'
    upstream.mkdir(exist_ok=True)
    for filename in ['utils.py','evaluation.py','LICENSE.md','HallusionBench.json','README.md']:
        shutil.copy2(ROOT/'upstream/HallusionBench'/filename,upstream/filename)
    info={'created_utc':datetime.now(timezone.utc).isoformat(),'stage':1,'models_actually_run':['OpenGVLab/InternVL3-2B'],
          'full_dataset_successful_raw_responses':integrity['successful_response_count'],'no_answer_grading_performed':True,
          'question_groups':455,'unique_images':346,'stage2_batches':len(batch_index),
          'omitted_assets':'All image pixels and model weights omitted. Image paths, hashes, source URLs and pinned download metadata included.'}
    (out/'package_summary.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    gpu_records=read(ROOT/'logs/gpu_monitor.jsonl') if (ROOT/'logs/gpu_monitor.jsonl').exists() else []
    physical_peak_mib=max((float(r['memory_used_mib_gpu_util_percent_temp_c_power_w'].split(',')[0]) for r in gpu_records),default=0)
    summary=f'''# 單模型實驗完成紀錄

唯一模型：OpenGVLab/InternVL3-2B，單張 RTX 3070 Ti 8GB。

- 完整資料：{integrity['record_count']}／1,129 題，非空白原始回答 {integrity['successful_response_count']} 題。
- 缺漏、重複、失敗與結構錯誤：全部為 0。
- Question Control Groups：455；圖片：346。
- 原始回答推論時間合計：{integrity['total_inference_seconds']/60:.2f} 分鐘（不含安裝、下載、模型載入與中斷間隔）。
- Tensor allocated 峰值：{integrity['max_peak_allocated_gib']:.3f} GiB。
- Reserved cache 峰值：{integrity['max_peak_reserved_gib']:.3f} GiB，含前 204 題預設快取策略；後續採 90% 上限及逐題清快取。
- NVIDIA 監測的實體顯存使用最高抽樣值：{physical_peak_mib:.0f} MiB；取樣間隔 20 秒，不代表捕捉所有瞬間峰值。
- 達到 128-token 上限：{len(integrity['outputs_at_token_limit'])} 題；完整生成原文與旗標皆保留，交第二階段處理。
- 分批判分輸入：{len(batch_index)} 批，完整控制分組不拆批。

沒有執行答案判定、Accuracy、Bias、Consistency 或診斷分析。成功產生回答不代表回答正確。

圖片來自 metadata 已逐筆核對的固定研究鏡像；原始 Drive 檔失效，無法獨立證明圖片位元與原檔完全一致。詳細來源、快取調整、環境與原始執行紀錄均保留。
'''
    (ROOT/'reports/EXPERIMENT_SUMMARY.md').write_text(summary,encoding='utf-8')
    roots=['configs','scripts','reports','logs','handoff','data/manifests',f'results/{RUN}']
    selected=[]
    for folder in roots:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.name not in ['run.lock','paper.txt','package_verification.json'] and path.suffix not in ['.png','.pdf']:
                selected.append(path)
    for filename in ['README.md','requirements.txt','requirements-lock.txt','.gitignore','.gitattributes','CITATION.cff','THIRD_PARTY_NOTICES.md']:
        path=ROOT/filename
        if path.exists(): selected.append(path)
    selected=sorted(set(selected))
    inventory=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in selected]
    archive=ROOT/'HallusionBench_Stage1_Results.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in selected: z.write(path,path.relative_to(ROOT).as_posix())
        z.writestr('PACKAGE_MANIFEST.json',json.dumps(inventory,indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in inventory:
            body=z.read(item['path'])
            assert hashlib.sha256(body).hexdigest()==item['sha256'],item['path']
            if item['path'].endswith('.jsonl'):
                for line in body.decode('utf-8').splitlines():
                    if line: json.loads(line)
        packed=[json.loads(line) for line in z.read(f'results/{RUN}/full/responses.jsonl').decode('utf-8').splitlines()]
        assert len(packed)==1129
    final={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),
           'members':len(inventory)+1,'zip_crc_passed':True,'all_member_sha256_passed':True,**info}
    (ROOT/'reports/package_verification.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
    print(json.dumps(final,indent=2))

if __name__=='__main__': main()
