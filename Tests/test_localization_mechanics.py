"""Exercise source-bound speech and the real per-file application boundary."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import foreigner_mechanics as speech
import localization_mechanics as mechanics

ROOT = speech.ROOT
LOCALES = 'th id cs hu nl fa ro hi fil el bg sr sw he'.split()


def values(locale):
    result = {}
    for collection, pattern in [('Dialogs', 'dialogue-batch-*.json'), ('UI', 'ui-batch-*.json')]:
        for p in (ROOT / 'Translations' / locale).glob(pattern):
            if '.validation.' not in p.name:
                result.update({(collection, r['id']): r['target'] for r in json.loads(p.read_text())['entries']})
    return result


class MechanicsTests(unittest.TestCase):
    def test_encoded_and_understood_boundaries(self):
        self.assertEqual(speech.encode('ABC xyz Ž', 'latin-atbash'), 'ZYX cba Ž')
        self.assertEqual(speech.encode('αω', 'greek-atbash'), 'ωα')
        for locale in LOCALES:
            rendered, authored = speech.checked_entries(locale)
            self.assertEqual(len(rendered), 64)
            self.assertTrue(all(v.startswith('Foreigner: ') for v in rendered.values()))
        with self.assertRaisesRegex(ValueError, 'non-Latin'):
            speech.encode('shalom שלום', 'romanized')
        self.assertEqual(speech.encode('shalom', 'romanized'), 'shalom')

    def test_real_policy_and_message_guards(self):
        for locale in LOCALES:
            actual = values(locale)
            mechanics.verify(locale, actual, ROOT / 'Translations' / locale)
            wrong = copy.copy(actual)
            wrong[('UI', mechanics.NOISE_ID)] = 'АБВ'
            with self.assertRaisesRegex(ValueError, 'Radio noise pool differs'):
                mechanics.verify(locale, wrong, ROOT / 'Translations' / locale)
            restored = copy.copy(actual)
            key = next(iter(speech.checked_entries(locale)[0]))
            restored[('Dialogs', key)] = 'Foreigner: ' + 'plain exposed speech'
            with self.assertRaisesRegex(ValueError, 'Foreigner mechanic differs'):
                mechanics.verify(locale, restored, ROOT / 'Translations' / locale)

    def test_failure_between_real_batch_replacements_and_continuation(self):
        # Real authored inputs and source/protected checks. Only the second
        # os.replace is fault-injected. No game/runtime dependency is exercised.
        (ROOT / 'outputs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='mechanics-test-', dir=ROOT / 'outputs') as temp:
            fixture = Path(temp)
            (fixture / 'Source').mkdir()
            (fixture / 'Source/preserve-exactly-v4.json').symlink_to(ROOT / 'Source/preserve-exactly-v4.json')
            target_dir = fixture / 'Translations/id'
            target_dir.mkdir(parents=True)
            shutil.copy2(ROOT / 'Translations/id/foreigner-mechanics-v1.json', target_dir)
            targets, _ = speech.checked_entries('id')
            # Reverse selected rows to the exact source preimage, so the test is
            # valid both before and after the development repair is applied.
            source = {r['id']: r['source'] for r in json.loads(speech.SPEC.read_text())['entries']}
            originals = {}
            for p in (ROOT / 'Translations/id').glob('dialogue-batch-*.json'):
                if '.validation.' in p.name:
                    continue
                d = json.loads(p.read_text())
                if not any(r['id'] in targets for r in d['entries']):
                    continue
                for r in d['entries']:
                    if r['id'] in targets:
                        r['target'] = source[r['id']]
                q = target_dir / p.name
                q.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
                originals[q] = q.read_bytes()
            calls = []
            real_replace = speech.os.replace
            def second_write_fails(a, b):
                calls.append(b)
                if len(calls) == 2:
                    raise OSError('injected second replacement failure')
                return real_replace(a, b)
            report_path = fixture / 'outputs/partial.json'
            with patch.object(speech, 'ROOT', fixture):
                with patch.object(speech.os, 'replace', second_write_fails):
                    with self.assertRaisesRegex(OSError, 'second replacement'):
                        speech.apply('id', report_path)
                report = json.loads(report_path.read_text())
                self.assertEqual(report['status'], 'preflight complete; application pending')
                self.assertEqual(sum('afterSha256' in row for row in report['changedFiles']), 1)
                self.assertNotEqual(calls[0].read_bytes(), originals[calls[0]])
                self.assertEqual(calls[1].read_bytes(), originals[calls[1]])
                # Reconcile only the verified task-owned, unapplied temp file.
                pending = calls[1].with_suffix('.mechanics-pending')
                expected = json.loads(originals[calls[1]])
                for row in expected['entries']:
                    if row['id'] in targets:
                        row['target'] = targets[row['id']]
                self.assertEqual(json.loads(pending.read_text()), expected)
                pending.unlink()
                speech.apply('id', fixture / 'outputs/continued.json')
                self.assertEqual({r['id']:r['target'] for p in target_dir.glob('dialogue-batch-*.json') for r in json.loads(p.read_text())['entries'] if r['id'] in targets}, targets)
                repeat = speech.apply('id', fixture / 'outputs/repeated.json')
                self.assertEqual(repeat['changedFiles'], 0)
                self.assertEqual(json.loads(report_path.read_text()), report)

    def test_authored_radio_outage_and_coverage_boundaries(self):
        actual = values('id')
        recipe = json.loads((ROOT / 'Translations/id/radio-mechanics-v1.json').read_text())
        source = json.loads(mechanics.RADIO_SPEC.read_text())['entries']
        damaged_id = next(r['id'] for r in source if '…' in r['source'])
        with tempfile.TemporaryDirectory(prefix='radio-guard-test-', dir=ROOT / 'outputs') as temp:
            directory = Path(temp)
            path = directory / 'radio-mechanics-v1.json'
            path.write_text(json.dumps(recipe, ensure_ascii=False))
            mechanics.verify('id', actual, directory)  # Matching positive control.
            changed = copy.deepcopy(recipe)
            row = next(r for r in changed['entries'] if r['id'] == damaged_id)
            row['target'] = row['target'].replace('…', '').replace('...', '')
            altered_values = copy.copy(actual)
            altered_values[('Dialogs', damaged_id)] = row['target']
            path.write_text(json.dumps(changed, ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, 'Authored radio outage removed'):
                mechanics.verify('id', altered_values, directory)
            incomplete = copy.deepcopy(recipe)
            incomplete['entries'].pop()
            path.write_text(json.dumps(incomplete, ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, 'Incomplete/duplicate radio message coverage'):
                mechanics.verify('id', actual, directory)


if __name__ == '__main__':
    unittest.main()
