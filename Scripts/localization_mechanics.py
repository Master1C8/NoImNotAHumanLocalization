"""Source-bound Foreigner and radio contracts shared by corpus/build gates.

These are development checks, not independent editorial or gameplay acceptance.
"""
import argparse
import json
import os
import re
from pathlib import Path

from foreigner_mechanics import ROOT, POLICY, checked_entries, digest, patch_targets

RADIO_SPEC = ROOT / 'Resources/Localization/radio-source-v1.json'
NOISE_ID = 56531188432228352


def verify(locale, values, directory):
    policy = json.loads(POLICY.read_text())['locales'][locale]
    foreigner, authored = checked_entries(locale)
    for key, target in foreigner.items():
        if values.get(('Dialogs', key)) != target:
            raise ValueError('Foreigner mechanic differs from authored boundaries: ' + str(key))
    if values.get(('UI', NOISE_ID)) != policy['radioNoise']:
        raise ValueError('Radio noise pool differs from locale policy')
    spec = json.loads(RADIO_SPEC.read_text())
    if spec['sourceInventorySha256'] != digest(ROOT / 'Source/localization-inventory-v3/strings.jsonl'):
        raise ValueError('Radio source inventory changed')
    radio_path = directory / 'radio-mechanics-v1.json'
    radio = json.loads(radio_path.read_text())
    if radio['schemaVersion'] != 1 or radio['locale'] != locale or radio['sourceSpecSha256'] != digest(RADIO_SPEC):
        raise ValueError('Radio authored identity/source changed')
    source = {r['id']: r for r in spec['entries']}
    targets = {r['id']: r for r in radio['entries']}
    if len(targets) != len(radio['entries']) or set(targets) != set(source) or len(source) != 52:
        raise ValueError('Incomplete/duplicate radio message coverage')
    for key, row in targets.items():
        if row['key'] != source[key]['key'] or values.get(('Dialogs', key)) != row['target']:
            raise ValueError('Radio message differs from authored draft: ' + str(key))
        # Cut words and unheard clauses remain authored, including at perfect tuning.
        # Localized word lengths differ; an exact count of ellipsis glyphs is not semantic evidence.
        if '…' in source[key]['source'] and not re.search(r'…|\.{3}', row['target']):
            raise ValueError('Authored radio outage removed: ' + str(key))
    return [authored, radio_path, POLICY, ROOT / 'Resources/Localization/foreigner-source-v1.json', RADIO_SPEC]


def apply_radio(locale, receipt):
    receipt = receipt.resolve()
    if not receipt.is_relative_to(ROOT / 'outputs') or receipt.exists():
        raise ValueError('Use a new canonical radio application receipt')
    target = json.loads(POLICY.read_text())['locales'][locale]['radioNoise']
    from preserve_exact import check_value
    rules = json.loads((ROOT / 'Source/preserve-exactly-v4.json').read_text())['tableRows']
    rule = next(r for r in rules if r['collection'] == 'UI' and int(r['stableId'].rsplit(':', 1)[1]) == NOISE_ID)
    check_value(rule, target)
    matches = []
    for path in sorted((ROOT / 'Translations' / locale).glob('ui-batch-*.json')):
        if '.validation.' in path.name:
            continue
        data = json.loads(path.read_text())
        for entry in data['entries']:
            if entry['id'] == NOISE_ID:
                matches.append((path, data, entry))
    if len(matches) != 1:
        raise ValueError('Radio noise ID missing or duplicated')
    path, data, entry = matches[0]
    before = entry['target']
    entry['target'] = target
    raw = patch_targets(path.read_text(), data, {NOISE_ID: target})
    report = {'locale': locale, 'path': str(path.relative_to(ROOT)), 'beforeSha256': digest(path),
              'before': before, 'after': target, 'policySha256': digest(POLICY), 'status': 'preflight complete; application pending'}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if digest(path) != report['beforeSha256']:
        raise ValueError('Radio UI batch changed during preflight')
    temp = path.with_suffix('.mechanics-pending')
    if temp.exists():
        raise ValueError('Reconcile prior partial radio write')
    temp.write_text(raw)
    os.replace(temp, path)
    report.update(afterSha256=digest(path), status='applied development draft; independent review pending')
    receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return {'locale': locale, 'radioNoise': target, 'changed': before != target}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('locale')
    parser.add_argument('--apply-radio', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    if args.apply_radio:
        if not args.receipt:
            parser.error('--apply-radio requires --receipt')
        result = apply_radio(args.locale, args.receipt)
    else:
        from locale_text_inputs import current_text
        values, files = current_text(args.locale, require_sidecars=False)
        result = {'locale': args.locale, 'rows': len(values), 'mechanics': 'passed development guards', 'runtime': 'not-run'}
    print(json.dumps(result, ensure_ascii=False))
