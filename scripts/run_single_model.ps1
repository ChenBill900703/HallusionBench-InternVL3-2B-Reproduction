$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONUTF8 = '1'
& '.venv/Scripts/python.exe' -u scripts/infer.py --config configs/internvl3_2b.json --smoke --retry-failed
if ($LASTEXITCODE -ne 0) { throw 'Smoke test failed; inspect results before full inference.' }
& '.venv/Scripts/python.exe' -u scripts/infer.py --config configs/internvl3_2b.json --retry-failed
if ($LASTEXITCODE -ne 0) { throw 'Full inference interrupted or failed; rerun the same command to resume.' }
& '.venv/Scripts/python.exe' scripts/verify_results.py --strict
if ($LASTEXITCODE -ne 0) { throw 'Coverage checks did not pass.' }
& '.venv/Scripts/python.exe' scripts/package_handoff.py
if ($LASTEXITCODE -ne 0) { throw 'Package verification failed.' }
