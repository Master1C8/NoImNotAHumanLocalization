#!/usr/bin/env python3
"""Reproduce root's read-only exact145-event chain; no semantic credit."""
import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];C=Path(__file__).resolve().parent
def main():
 receipt=json.loads((C/'author-chain.json').read_text());p=ROOT/receipt['verifierPath']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['verifierSha256']
 spec=importlib.util.spec_from_file_location('root_author_chain',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);actual=m.verify(7)
 assert all(receipt[k]==v for k,v in actual.items())
 assert actual['targetOnlyCorrectionEvents']==145 and actual['authoredFiles']==456 and actual['firstPassUnits']==16538
 print(json.dumps({'authorChain':'passed','targetOnlyEvents':145,'priorEvents':143,'newEvents':2,'exactFirstPassFiles':456,'semanticCredit':0}))
if __name__=='__main__':main()
