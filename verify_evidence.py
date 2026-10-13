"""Read-only integrity and recorded-result verification; does not run the lab."""
from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT/'projects/ip-cctv-recording'

def main():
    failures=[]
    manifest=ROOT/'SHA256SUMS.txt'
    entries={}
    for line in manifest.read_text().splitlines():
        expected,name=line.split('  ',1)
        path=ROOT/name
        if Path(name).is_absolute() or '..' in Path(name).parts:
            failures.append('Unsafe manifest path');continue
        entries[name]=expected
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            failures.append('Missing/changed file: '+name)
    current={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts and p.name!='SHA256SUMS.txt'}
    if current!=set(entries):failures.append('Release file list differs from manifest')
    for name,count in [('before-recovery.json',13),('fault-recovery.json',3),('after-recovery.json',13)]:
        data=json.loads((PROJECT/'evidence'/name).read_text())
        if not data['passed'] or len(data['checks'])!=count or not all(x['pass'] for x in data['checks']):
            failures.append('Recorded checks do not pass: '+name)
        for row in data['checks']:
            def logs(v):
                if isinstance(v,dict):
                    for x in v.values():yield from logs(x)
                elif isinstance(v,list):
                    for x in v:yield from logs(x)
                elif isinstance(v,str) and v.startswith('logs/'):yield v
            for log in logs(row):
                if not (PROJECT/log).is_file():failures.append('Referenced log missing: '+log)
    final=json.loads((PROJECT/'evidence/after-recovery.json').read_text())
    for cam in ['cam01','cam02']:
        row=next(x for x in final['checks'] if x['name']==cam+' exported playback decode')['detail']
        path=PROJECT/'evidence/videos'/(cam+'-verified.mp4')
        if path.stat().st_size!=row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            failures.append('Export differs from recorded result: '+cam)
        if row['exit']!=0 or row['decoded_frames']!=50:failures.append('Unexpected recorded decode: '+cam)
    with (PROJECT/'evidence/test-results.csv').open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    if len(rows)!=29 or any(x['passed']!='True' for x in rows):failures.append('Stage table does not match expected 29 passing rows')
    commission=json.loads((PROJECT/'evidence/commissioning-result.json').read_text())
    if not commission['passed'] or not commission['services_stopped_after_test']:failures.append('Unexpected commissioning result')
    if failures:
        for item in failures:print('FAIL:',item)
        return 1
    print('PASS: release manifest, recorded 13/3/13 results, referenced logs and both export hashes.')
    print('Read-only evidence check; personal execution relies on the contribution record and reviewed run, not hashes alone.')
    return 0

if __name__=='__main__':sys.exit(main())
