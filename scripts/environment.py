import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
import psutil
import torch

root = Path(__file__).resolve().parents[1]
packages = {d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
info = {'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),
        'cpu':os.environ.get('PROCESSOR_IDENTIFIER'),'logical_cpus':psutil.cpu_count(),
        'physical_cpus':psutil.cpu_count(logical=False),'ram':psutil.virtual_memory()._asdict(),
        'disk':psutil.disk_usage(str(root))._asdict(),'torch':torch.__version__,
        'cuda_available':torch.cuda.is_available(),'cuda_runtime':torch.version.cuda,
        'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'nvidia_smi':subprocess.check_output(['nvidia-smi'],text=True,encoding='utf-8'), 'packages':packages}
if torch.cuda.is_available():
    x = torch.arange(16,device='cuda',dtype=torch.bfloat16).reshape(4,4)
    info['cuda_computation_test']=(x @ x).float().cpu().tolist()
    info['bf16_supported']=torch.cuda.is_bf16_supported()
(root/'reports/environment.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
(root/'requirements-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),encoding='utf-8')
print(json.dumps({k:v for k,v in info.items() if k not in {'packages','nvidia_smi'}},indent=2))
