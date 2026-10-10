"""Apply and verify model-authored Foreigner speech without generating wording.

Opaque/understood boundaries are editorial inputs, not script guesses. Historical
audit/validation receipts are never overwritten. Outputs remain development drafts.
"""
import argparse
import hashlib
import json
import os
import re
import string
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'Resources/Localization/mechanics-v1.json'
SPEC = ROOT / 'Resources/Localization/foreigner-source-v1.json'
INVENTORY = ROOT / 'Source/localization-inventory-v3/strings.jsonl'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(text, method):
    if method == 'romanized':
        if any(unicodedata.category(c).startswith('L') and 'LATIN' not in unicodedata.name(c, '') for c in text):
            raise ValueError('Romanized opaque wording contains a non-Latin letter')
        return text
    alphabets = {
        'latin-atbash': string.ascii_lowercase,
        'greek-atbash': 'αβγδεζηθικλμνξοπρστυφχψω',
        'bulgarian-atbash': 'абвгдежзийклмнопрстуфхцчшщъьюя',
        'serbian-atbash': 'абвгдђежзијклљмнњопрстћуфхцчџш',
    }
    alphabet = alphabets[method]
    if method == 'greek-atbash':
        # Normalize final sigma and strip accents only inside opaque speech.
        # Accented understood words retain their exact authored spelling.
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c)).replace('ς', 'σ')
    return text.translate(str.maketrans(alphabet + alphabet.upper(), alphabet[::-1] + alphabet[::-1].upper()))


def render(entry, method):
    if not entry['parts']:
        raise ValueError('Missing authored speech parts')
    values = []
    for part in entry['parts']:
        if part['kind'] not in {'opaque', 'understood'} or not isinstance(part['text'], str) or not part['text']:
            raise ValueError('Invalid authored speech part')
        values.append(encode(part['text'], method) if part['kind'] == 'opaque' else part['text'])
    return 'Foreigner: ' + ''.join(values)


def patch_targets(raw, expected, targets):
    """Replace JSON target literals while preserving unrelated bytes/formatting."""
    matched = set()
    def replace(match):
        key = int(match['id'])
        if key not in targets:
            return match[0]
        if key in matched:
            raise ValueError('Duplicate JSON target ID')
        matched.add(key)
        return match['prefix'] + json.dumps(targets[key], ensure_ascii=False)
    patched = re.sub(r'(?P<prefix>"id"\s*:\s*(?P<id>\d+)\s*,\s*"target"\s*:\s*)(?:"(?:\\.|[^"\\])*")', replace, raw)
    if matched != set(targets) or json.loads(patched) != expected:
        raise ValueError('JSON target patch did not match the preflighted document')
    return patched


def checked_entries(locale):
    policy = json.loads(POLICY.read_text())['locales'][locale]
    spec = json.loads(SPEC.read_text())
    if spec['sourceInventorySha256'] != digest(INVENTORY):
        raise ValueError('Foreigner source inventory changed')
    authored_path = ROOT / 'Translations' / locale / 'foreigner-mechanics-v1.json'
    authored = json.loads(authored_path.read_text())
    if authored['schemaVersion'] != 1 or authored['locale'] != locale or authored['sourceSpecSha256'] != digest(SPEC):
        raise ValueError('Foreigner authored identity/source changed')
    source = {r['key']: r for r in spec['entries']}
    target = {r['key']: r for r in authored['entries']}
    if len(target) != len(authored['entries']) or set(target) != set(source):
        raise ValueError('Incomplete/duplicate Foreigner speech coverage')
    result = {}
    for key, row in source.items():
        entry = target[key]
        understood = [p.get('sourceCue') for p in entry['parts'] if p['kind'] == 'understood']
        if understood != row['understoodCues']:
            raise ValueError('Understood/opaque source boundary changed: ' + key)
        if row['opaque'] != any(p['kind'] == 'opaque' for p in entry['parts']):
            raise ValueError('Opaque speech exposed or understood speech masked: ' + key)
        result[row['id']] = render(entry, policy['foreigner'])
    return result, authored_path


def apply(locale, receipt_path):
    receipt_path = receipt_path.resolve()
    if not receipt_path.is_relative_to(ROOT / 'outputs') or receipt_path.exists():
        raise ValueError('Use a new canonical mechanics application receipt')
    targets, authored = checked_entries(locale)
    seen = set()
    changes = []
    pending = []
    from preserve_exact import check_value
    rules = {int(r['stableId'].rsplit(':', 1)[1]): r for r in json.loads((ROOT / 'Source/preserve-exactly-v4.json').read_text())['tableRows'] if r['collection'] == 'Dialogs'}
    for key, target in targets.items():
        check_value(rules[key], target)
    for path in sorted((ROOT / 'Translations' / locale).glob('dialogue-batch-*.json')):
        if '.validation.' in path.name:
            continue
        data = json.loads(path.read_text())
        changed = []
        for entry in data['entries']:
            key = entry['id']
            if key not in targets:
                continue
            if key in seen:
                raise ValueError('Duplicate batch speech ID')
            seen.add(key)
            if entry['target'] != targets[key]:
                changed.append({'id': key, 'before': entry['target'], 'after': targets[key]})
                entry['target'] = targets[key]
        if changed:
            changes.append({'path': str(path.relative_to(ROOT)), 'beforeSha256': digest(path), 'changes': changed})
            replacements = {r['id']: r['after'] for r in changed}
            pending.append((path, patch_targets(path.read_text(), data, replacements), changes[-1]))
    if seen != set(targets):
        raise ValueError('Foreigner target IDs absent from batches')
    # Preflight the complete set before the first write. Each replacement is
    # atomic; the complete set is not a transaction. Preserve the delta receipt.
    for path, text, receipt in pending:
        if digest(path) != receipt['beforeSha256']:
            raise ValueError('Authored batch changed during preflight')
    report = {'locale': locale, 'status': 'preflight complete; application pending',
              'authoredPath': str(authored.relative_to(ROOT)), 'authoredSha256': digest(authored),
              'sourceSpecSha256': digest(SPEC), 'policySha256': digest(POLICY), 'changedFiles': changes,
              'atomicity': 'per-file replacement; multi-file application is not a transaction'}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for path, text, receipt in pending:
        if digest(path) != receipt['beforeSha256']:
            raise ValueError('Authored batch changed during application')
        temp = path.with_suffix('.mechanics-pending')
        if temp.exists():
            raise ValueError('Reconcile prior partial mechanics write')
        temp.write_text(text)
        os.replace(temp, path)
        receipt['afterSha256'] = digest(path)
        receipt_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    report['status'] = 'applied development draft; independent review pending'
    receipt_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return {'locale': locale, 'changedFiles': len(changes), 'receipt': str(receipt_path.relative_to(ROOT))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('locale')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    if args.apply and not args.receipt:
        parser.error('--apply requires --receipt to preserve the plan before writing')
    print(json.dumps(apply(args.locale, args.receipt) if args.apply else {'locale': args.locale, 'entries': len(checked_entries(args.locale)[0])}, ensure_ascii=False))
