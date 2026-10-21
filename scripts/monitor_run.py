"""Low-overhead system measurements for the single authorized run."""
import json
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path

root=Path(__file__).resolve().parents[1]
lock=root/'results/internvl3_2b_bf16_tiles12/full/run.lock'
with open(root/'logs/gpu_monitor.jsonl','a',encoding='utf-8') as f:
    while lock.exists():
        output=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw','--format=csv,noheader,nounits'],text=True).strip()
        f.write(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat(),'memory_used_mib_gpu_util_percent_temp_c_power_w':output})+'\n')
        f.flush()
        time.sleep(20)
