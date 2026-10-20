#!/usr/bin/env python3
"""Add bounded runtime layout repairs to a verified text-only locale package.

Authored strings and preserved syntax stay unchanged. Reopen every serialized
object in the changed file and compare the exact expected field mutations.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import UnityPy

from probe_assets import ROOT, DEFAULT_GAME, EXPECTED_UNITY, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree
from build_locale_probe import save_verified
from locale_text_inputs import accepted_inputs, project_path

MENU = {'NewGame': 1958, 'Continue': 2087, 'Quit': 2108, 'Collection': 2155, 'Settings': 2181}


def menu_layout(tree):
    require(tree['m_enableAutoSizing'] == 1 and tree['m_fontSizeMin'] == 24.0 and
            tree['m_fontSizeMax'] == 28.0 and tree['m_margin'] == {'x': 20.0, 'y': 0.0, 'z': 20.0, 'w': 0.0},
            'Menu layout differs from the pinned original; reject ambiguous old/new state')
    result = copy.deepcopy(tree)
    result['m_fontSizeMin'] = 16.0
    result['m_margin']['x'] = result['m_margin']['z'] = 8.0
    return result


def build(package, output):
    require(package.is_relative_to(ROOT / 'outputs') and output.is_relative_to(ROOT / 'outputs') and
            not output.exists(), 'Use a verified canonical package and a new output directory')
    report = json.loads((package / 'report.json').read_text())
    verification = json.loads((package / 'verification.json').read_text())
    require(verification['result'] == 'passed' and verification['reportSha256'] == digest(package / 'report.json') and
            len(report['artifacts']) == 31 and report['translatedTextValues'] == 16538 and
            verification['translatedTextValuesCompared'] == 16538, 'Parent package is not fully verified')
    text_report = json.loads(project_path(report['textReportPath']).read_text())
    accepted_inputs(report['locale'], project_path(text_report['semanticAcceptancePath']),
                    project_path(text_report['exactReportPath']))
    require(all(digest(package / name) == row['sha256'] for name, row in report['artifacts'].items()),
            'Verified package payload changed')
    source_pins = json.loads((ROOT / 'outputs/th-fresh-install-preflight-v3/report.json').read_text())['originalFileHashes']
    require(all(digest(DEFAULT_GAME / name) == sha for name, sha in source_pins.items()), 'Original game changed')
    scope = json.loads((ROOT / 'Documentation/static-text-scope-v2.json').read_text())['rows']
    for name, pid in MENU.items():
        rows = [r for r in scope if r['stableId'] == f'tmp:level0:{pid}:m_text']
        require(len(rows) == 1 and any(a['name'] == name for a in rows[0]['sceneAncestry']) and
                len(rows[0]['localizedStringBindings']) == 1, 'Menu source ownership changed')
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME / 'NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed'))
    source = UnityPy.load(str(DEFAULT_GAME / 'NoImNotAHuman_Data/level0'))
    source.typetree_generator = generator
    env = UnityPy.load(str(package / 'NoImNotAHuman_Data/level0'))
    original = {o.path_id: o.get_raw_data() for o in env.objects}
    generated, changes = {}, []
    for name, pid in MENU.items():
        _, schema = generated_tree(source.file.objects[pid])
        obj = env.file.objects[pid]
        before = obj.read_typetree(nodes=schema)
        after = menu_layout(before)
        obj.save_typetree(after, nodes=schema)
        generated[pid] = (schema, after)
        changes.append({'component': f'level0:{pid}', 'menuAction': name,
                        'before': {'m_fontSizeMin': before['m_fontSizeMin'], 'm_margin': before['m_margin']},
                        'after': {'m_fontSizeMin': after['m_fontSizeMin'], 'm_margin': after['m_margin']},
                        'allOtherFieldsUnchanged': True})
    output.mkdir(parents=True)
    for name, row in report['artifacts'].items():
        if name == 'NoImNotAHuman_Data/level0': continue
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package / name, target)
        require(digest(target) == row['sha256'], 'Copied payload differs')
    saved = save_verified(env, output / 'NoImNotAHuman_Data/level0',
                          {'original': original, 'allowed': set(MENU.values())}, generated)
    final = copy.deepcopy(report)
    final.update(status='one-locale text package with verified menu text-fit repair; runtime pending',
                 parentPackageReport=str((package / 'report.json').relative_to(ROOT)),
                 parentPackageReportSha256=digest(package / 'report.json'),
                 parentVerificationSha256=digest(package / 'verification.json'),
                 runtimeBuilderSha256=digest(Path(__file__)), runtimeLayoutChanges=changes,
                 originalFileHashes=source_pins, authoredTextChanged=False)
    final['artifacts']['NoImNotAHuman_Data/level0'] = {'sha256': saved['sha256'], 'layer': 'runtime-layout'}
    (output / 'report.json').write_text(json.dumps(final, ensure_ascii=False, indent=2) + '\n')
    check = {'result': 'passed', 'locale': report['locale'], 'reportSha256': digest(output / 'report.json'),
             'parentSerializedVerificationReusedOnExactPayloadHashes': True,
             'artifactHashesCompared': 31, 'translatedTextValuesCompared': 16538,
             'layoutModifiedObjects': len(MENU), 'allOtherModifiedObjectFieldsUnchanged': True,
             'savedSceneObjects': saved, 'runtime': 'not-run', 'visualReview': 'pending'}
    (output / 'verification.json').write_text(json.dumps(check, indent=2) + '\n')
    require(all(digest(output / name) == row['sha256'] for name, row in final['artifacts'].items()),
            'Final runtime package differs')
    require(all(digest(DEFAULT_GAME / name) == sha for name, sha in source_pins.items()), 'Original game changed during build')
    print(json.dumps({'locale': report['locale'], 'layoutObjects': len(MENU), 'artifacts': 31,
                      'output': str(output.relative_to(ROOT)), 'runtime': 'pending'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.package.resolve(), args.output.resolve())
