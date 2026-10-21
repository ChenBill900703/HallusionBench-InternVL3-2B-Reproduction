"""Create and reopen a self-contained Stage 2 results archive with SHA-256 inventory."""
import json,hashlib,zipfile
from compute_metrics import ROOT,S2,dump
def main():
    files=[p for p in sorted(S2.rglob('*')) if p.is_file() and not any(x in p.parts for x in ['__pycache__','logs']) and p.suffix not in ['.pyc','.tmp'] and p.name not in ['PACKAGE_MANIFEST.json','package_verification.json']]
    inventory=[{'path':'stage2/'+p.relative_to(S2).as_posix(),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    manifest={'format_version':1,'description':'InternVL3-2B Stage 2 real-response semantic evaluation; no other model inference','files':inventory,'file_count':len(inventory),'excluded':'model weights, environment, all 346 source images (10 verified case images are included), original paper PDF, installation/console logs, Stage 1 ZIP','reproduce':'See stage2/README.md; recompute from saved judgments with no API or GPU'}
    dump(S2/'PACKAGE_MANIFEST.json',manifest)
    dest=ROOT/'HallusionBench_Stage2_Results.zip'
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'stage2/'+p.relative_to(S2).as_posix())
        z.write(S2/'PACKAGE_MANIFEST.json','stage2/PACKAGE_MANIFEST.json')
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for f in inventory:
            data=z.read(f['path']);assert len(data)==f['size'] and hashlib.sha256(data).hexdigest()==f['sha256']
        assert len(z.namelist())==len(inventory)+1
    verification={'passed':True,'archive':dest.name,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'verified_payload_files':len(inventory),'zip_members':len(inventory)+1,'crc_passed':True,'all_manifest_sizes_and_sha256_passed':True}
    dump(S2/'reports/package_verification.json',verification);print(json.dumps(verification,indent=2))
if __name__=='__main__':main()
