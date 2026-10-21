param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force tmp,logs,reports,data,results,handoff | Out-Null
$env:TEMP = (Resolve-Path tmp).Path
$env:TMP = $env:TEMP
$env:PYTHONUTF8 = '1'
& $Python -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), 'Use Python 3.10-3.12; this experiment used 3.12.'"
if ($LASTEXITCODE -ne 0) { throw 'Unsupported Python.' }
& $Python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Could not create virtual environment.' }
& '.venv/Scripts/python.exe' -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch install failed.' }
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }
& '.venv/Scripts/python.exe' scripts/environment.py
