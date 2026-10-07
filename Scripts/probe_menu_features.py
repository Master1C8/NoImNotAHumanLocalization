#!/usr/bin/env python3
"""Bounded existing-TMP-feature hypothesis; no font/text or source writes."""
import argparse
import json
from pathlib import Path
import UnityPy
from probe_assets import DEFAULT_GAME, ROOT, EXPECTED_UNITY, UI_ID, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree, serialized_bytes


def run(output):
    require(output.is_relative_to(ROOT/'outputs'), 'Noncanonical output')
    source=DEFAULT_GAME/'NoImNotAHuman_Data/level0'
    original_hash=digest(source)
    env=UnityPy.load(str(source))
    generator=CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME/'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    env.typetree_generator=generator
    localized,_=generated_tree(env.file.objects[1956])
    require(localized['m_StringReference']['m_TableEntryReference']['m_KeyId']==UI_ID, 'Different menu binding')
    obj=env.file.objects[1958];tree,schema=generated_tree(obj)
    require(tree['m_GameObject']==localized['m_GameObject'] and tree['m_text']=='Start', 'Different menu component')
    before={o.path_id:serialized_bytes(o) for o in env.objects}
    features=list(tree['m_ActiveFontFeatures'])
    liga=int.from_bytes(b'liga','big')
    require(liga not in features,'Hypothesis already enabled')
    tree['m_ActiveFontFeatures'].append(liga)
    obj.save_typetree(tree,nodes=schema)
    expected={o.path_id:serialized_bytes(o) for o in env.objects}
    require(all(expected[k]==raw for k,raw in before.items() if k!=obj.path_id),'Unrelated object changed')
    output.mkdir(parents=True,exist_ok=False)
    artifact=output/'level0';artifact.write_bytes(env.file.save())
    reopened=UnityPy.load(str(artifact))
    require({o.path_id:o.get_raw_data() for o in reopened.objects}==expected,'Saved bytes differ')
    require(reopened.file.objects[1958].read_typetree(nodes=schema)==tree,'Feature fields differ')
    require(digest(source)==original_hash,'Source changed')
    report={'hypothesis':'Enable existing TMP liga on localized menu button; compare the unchanged Hindi text/font in runtime.',
            'sourceSha256':original_hash,'artifactSha256':digest(artifact),'changedObject':1958,
            'oldFeatures':features,'newFeatures':tree['m_ActiveFontFeatures'],
            'unchangedOtherObjectsVerified':True,'runtime':'not-run'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output.resolve())
