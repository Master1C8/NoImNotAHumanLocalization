#!/usr/bin/env python3
"""Verify cycle006 immutable receipt and current full-pair input pins."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];C=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=json.loads((C/'completion-manifest.json').read_text())
 for pin in manifest['files']+manifest['currentExternalPins']:
  assert sha(ROOT/pin['path'])==pin['sha256'],pin['path']
 listed={pin['path'] for pin in manifest['files']}
 actual={str(p.relative_to(ROOT)) for p in C.rglob('*') if p.is_file() and p.name!='completion-manifest.json'}
 assert actual==listed,{'unlisted':sorted(actual-listed),'missing':sorted(listed-actual)}
 assert (ROOT/'Translations/fil/progress.json').read_bytes()==(C/'after-progress.json').read_bytes()
 h=json.loads((C/'handoff.json').read_text());c=json.loads((C/'closure.json').read_text())
 for name,digest in h['artifactPins'].items():assert sha(C/name)==digest,name
 ids=(C/'next-review-ids.txt').read_text().splitlines();pairs=[json.loads(line) for line in (C/'next-delta-paired.jsonl').read_text().splitlines()]
 assert ids==c['exactNextDelta']['ids']==[p['stableId'] for p in pairs] and len(ids)==len(set(ids))==423
 assert c['unexplainedMissingIds']==c['unexplainedExtraIds']==[]
 print(json.dumps({'completionManifestSha256':sha(C/'completion-manifest.json'),'cycleFiles':len(manifest['files']),'currentExternalPins':len(manifest['currentExternalPins']),'nextReviewPairs':423,'seal':'passed','independentAcceptance':False,'runtime':'not-run'}))
if __name__=='__main__':main()
