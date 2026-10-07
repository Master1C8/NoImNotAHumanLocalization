#!/usr/bin/env python3
"""Install a complete verified probe into the stopped, exact isolated fixture."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from probe_assets import ROOT, digest, require

FIXTURE = ROOT/'runtime/No Human Probe.app'
GAME = FIXTURE/'Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human'


def install(build, previous, output):
    require(build.is_relative_to(ROOT/'outputs') and output.is_relative_to(ROOT/'outputs'), 'Canonical output scope required')
    report = json.loads((build/'report.json').read_text())
    prior = {r['relativePath']: r['after'] for r in json.loads(previous.read_text())['files']}
    processes = subprocess.run(['ps','-axo','pid,command'], check=True, text=True, stdout=subprocess.PIPE).stdout
    require(not any(str(FIXTURE) in line or 'NoImNotAHuman.exe' in line for line in processes.splitlines()), 'Fixture or ambiguous game process is running')
    expected = report['artifacts']
    require(set(expected)==set(prior), 'Prior installed file set differs')
    rows=[]
    for rel, details in expected.items():
        source=build/rel
        dest=GAME/rel
        require(source.resolve().is_relative_to(build) and dest.resolve().is_relative_to(FIXTURE.resolve()), 'File escaped isolated scope')
        require(digest(source)==details['sha256'], 'Build artifact changed')
        require(digest(dest)==prior[rel], 'Unexpected owner/fixture change: '+rel)
        rows.append({'relativePath':rel,'before':prior[rel],'after':details['sha256']})
    output.mkdir(parents=True,exist_ok=False)
    receipt={'buildReport':str((build/'report.json').relative_to(ROOT)), 'fixture':str(FIXTURE), 'files':rows,
             'allInstalledHashesVerified':False,
             'commitBoundary':'Per-file atomic replacements in stopped fixture; no multi-file transaction. Do not launch before full verification.'}
    def record():
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    record()
    for row in rows:
        rel=row['relativePath'];dest=GAME/rel;backup=output/rel
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
        temporary=dest.with_name(dest.name+'.probe-tmp')
        require(not temporary.exists(), 'Unreconciled previous temporary replacement')
        shutil.copy2(build/rel,temporary);temporary.replace(dest)
    for row in rows:
        require(digest(GAME/row['relativePath'])==row['after'], 'Installed hash mismatch')
    receipt['allInstalledHashesVerified']=True;record()
    print(json.dumps({'receipt':str(output/'receipt.json'),'files':len(rows),'verified':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--previous-receipt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    install(args.build.resolve(),args.previous_receipt.resolve(),args.output.resolve())
