#!/usr/bin/env python3
"""Invoke the unchanged owning batch validator sequentially for affected fil inputs only."""
import contextlib,hashlib,io,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];CYCLE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Scripts'))
import validate_game_text_batch as owning

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=CYCLE/'affected-validation.json';assert not out.exists()
 plan=json.load(open(CYCLE/'plan.json'));before=json.load(open(CYCLE/'preimage-pins.json'));validator=ROOT/'Scripts/validate_game_text_batch.py';h=sha(validator);reports=[]
 for record in plan['files']:
  path=ROOT/record['authoredPath'];side=ROOT/record['validationPath']
  assert sha(path)==record['afterSha256'] and sha(side)==record['beforeValidationSha256'] and sha(ROOT/record['beforeValidationSnapshotPath'])==record['beforeValidationSha256']
  sys.argv=[str(validator),str(path)]
  with contextlib.redirect_stdout(io.StringIO()):owning.main()
  r=json.load(open(side));assert r['locale']=='fil' and r['structuralResult']=='passed' and r['batchSha256']==sha(path)
  reports.append(dict(r,sidecarPath=str(side.relative_to(ROOT)),sidecarSha256=sha(side)))
 assert sha(validator)==h
 out.write_text(json.dumps({'schemaVersion':1,'locale':'fil','affectedBatches':len(reports),'status':'all affected owning guards passed','owningValidatorPath':str(validator.relative_to(ROOT)),'owningValidatorSha256':h,'execution':'sequential exact owning main; affected fil inputs only, no parse pools or all-locale scan','reports':reports},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'affectedBatches':len(reports),'checkedAffectedRows':sum(r['authoredRows'] for r in reports),'result':'passed'}))
if __name__=='__main__':main()
