"""Persist independently read evidence; never mutate source, locale, or old audits."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'Translations/hu/semantic-correction-cycle-01'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(name, value):
    path = OUT / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

spec = importlib.util.spec_from_file_location('closure', OLD / 'build-closure.py')
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)
plan, first, selectors, preserve, order, source, before, after, files = closure.corpus()
rows = [json.loads(line) for line in (OLD / 'evidence/closure-review-rows.jsonl').read_text().splitlines()]
assert len(rows) == 2902
handoff = json.loads((OLD / 'independent-review-handoff.json').read_text())
pins = []
def check_pins(value):
    if isinstance(value, dict):
        for key, path in value.items():
            if key.endswith('Path') and isinstance(path, str):
                expected = value.get(key[:-4] + 'Sha256')
                if expected:
                    actual = sha((ROOT / path).read_bytes())
                    assert actual == expected, path
                    pins.append({'path': path, 'expectedSha256': expected, 'actualSha256': actual})
            elif key == 'path' and value.get('sha256'):
                actual = sha((ROOT / path).read_bytes())
                assert actual == value['sha256'], path
                pins.append({'path': path, 'expectedSha256': value['sha256'], 'actualSha256': actual})
            check_pins(path)
    elif isinstance(value, list):
        for item in value:
            check_pins(item)
check_pins(handoff)
glossary = ROOT / 'Documentation/glossary-translations/hu/layer.json'
canonical = Path('/Users/antonkrutov/Desktop/SiteForMods/data/games/no-im-not-a-human/glossary.json')
write('pins.json', {'handoffSha256': sha((OLD / 'independent-review-handoff.json').read_bytes()),
                    'verifiedHandoffPins': pins, 'currentAuthoredFileHashes': files,
                    'glossaryLayerSha256': sha(glossary.read_bytes()),
                    'canonicalGlossarySha256': sha(canonical.read_bytes()),
                    'corpusRecipeVerifiedSourceAndFirstPass': True,
                    'acceptedUnits': len(order), 'firstPassSegments': len(first['segments']),
                    'changedIds': len(plan['rows'])})

# Each replacement is the complete unit and preserves all other authored wording.
changes = {
    461: ('Több a kén.', 'Több a fülzsír.', 'ear-wax',
          'Russian сера is earwax in the TV_Ear branch. Approved ear-wax explicitly rejects industrial sulfur; kén changes the referent.'),
    464: ('Csak a kén marad.', 'Csak a fülzsír marad.', 'ear-wax',
          'Russian сера refers back to material growing in ears; kén means sulfur and contradicts approved Fülzsír.'),
    685: ('A húgomnak', 'A lánytestvéremnek', 'sisters-together',
          'Source сестрёнке marks a female sibling affectionately, not a younger sibling; húgom invents birth order.'),
    688: ('a húgomnak', 'a lánytestvéremnek', 'sisters-together',
          'Source сестры specifies a sister with no birth order; húgom adds younger age.'),
    689: ('a húgomnak', 'a lánytestvéremnek', 'sisters-together',
          'Source сестре specifies a sister with no birth order; húgom adds younger age.'),
    700: ('a húgommal', 'a lánytestvéremmel', 'sisters-together',
          'Source сестрёнку specifies a female sibling affectionately; no source or approved character entry establishes younger age.'),
    1063: ('Itt {0}.', 'Itt van {0}.', 'runtime-resident-copula',
           'A locative Hungarian assertion needs van. Substituting any bare characterName label leaves the current clause without its verb.'),
    1075: ('Itt már {0}.', 'Itt már {0} van.', 'runtime-resident-copula',
           'The locative assertion Здесь уже {0} requires van in Hungarian. Name labels contain no missing copula.'),
    1320: ('nem melege van', 'nincs melege', 'negative-have-temperature',
           'The idiom melege van is negated as nincs melege; current nem melege van instead negates focused melege and creates an unsupported contrast.'),
    1323: ('nem melege van', 'nincs melege', 'negative-have-temperature',
           'The repeated lack-of-heat condition requires nincs melege; source gives no contrast to support nem melege van.'),
    1844: ('az én kis feleségemnek fütyül', 'az én kis feleségem fütyül', 'couple-husband',
           'Fütyül valakire takes a nominative subject. Current feleségemnek is dative and leaves the wife incorrectly attached to the predicate.'),
    2349: ('Pedig a hónaljammal nincs semmi baj.', 'Pedig a hónaljban nincs semmi szégyellnivaló.', 'cultist-two',
           'The shame statement and next line about the awkward word concern embarrassment, not a claim that this character has no bodily defect.'),
    2762: ('A kívánt helyre', 'Kívánságlistára', 'wishlist-action',
           'The UI action В желаемое means adding to the wishlist; current target says to the desired place.'),
    2815: ('KRITIKUS REFLEX!', 'CRITICAL REFLEX!', 'publisher-proper-name',
           'CRITICAL REFLEX is the credited publisher name, also retained in the source credits; translating its first word changes that proper name.')
}
findings = []
for index, (old, new, concept, reason) in changes.items():
    row = rows[index]
    assert row['after'].count(old) == 1, (index, row['key'])
    target = row['after'].replace(old, new)
    findings.append({'stableId': row['stableId'], 'key': row['key'], 'source': row['source'],
                     'currentTarget': row['after'], 'proposedTarget': target,
                     'reason': reason, 'concept': concept, 'context': row['nodeNames'],
                     'authoredFile': row['authoredFile'], 'authoredFileSha256': row['afterAuthoredFileSha256'],
                     'reviewClosureOrdinal': index, 'status': 'proposal; author adjudication required'})
write('consolidated-proposals.json', {'schemaVersion': 1, 'locale': 'hu',
      'status': 'one consolidated objective proposal batch; no application',
      'sourceInventorySha256': plan['sourceInventorySha256'],
      'glossaryLayerSha256': sha(glossary.read_bytes()), 'closureRowsSha256': sha((OLD / 'evidence/closure-review-rows.jsonl').read_bytes()),
      'findings': findings})

compiled = json.loads((OUT / 'compiled-context.json').read_text())
occurrences = {}
for node in compiled['nodes']:
    for instruction in node.get('instructions', []):
        for operand in instruction['operands']:
            if isinstance(operand, str) and operand.startswith('line:'):
                occurrences.setdefault(operand, []).append({'node': node['node'], 'instruction': instruction['index'], 'opcode': instruction['opcode']})
proposed = {r['stableId'] for r in findings}
read_evidence = []
for i, row in enumerate(rows):
    assert source[row['stableId']]['source'] == row['source']
    assert after[row['stableId']]['target'] == row['after']
    assert sha((ROOT / row['authoredFile']).read_bytes()) == row['afterAuthoredFileSha256']
    read_evidence.append({'closureOrdinal': i, 'stableId': row['stableId'], 'key': row['key'],
          'source': row['source'], 'currentTarget': row['after'],
          'sourceSha256': sha(row['source'].encode()), 'targetSha256': sha(row['after'].encode()),
          'authoredFile': row['authoredFile'], 'authoredFileSha256': row['afterAuthoredFileSha256'],
          'components': row['components'], 'sourceNodeNames': row['nodeNames'],
          'compiledOccurrences': occurrences.get(row['key'], []),
          'fullPairRead': True, 'reader': '/root/hu_independent_review_01',
          'verdict': 'objective-correction-proposed' if row['stableId'] in proposed else 'no-objective-text-change-proposed',
          'contextLimits': 'Saved compiled instruction order, source and glossary; no runtime reachability or layout claim.'})
path = OUT / 'full-pair-read-evidence.jsonl'
assert not path.exists()
path.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in read_evidence))
write('read-summary.json', {'fullPairReadUnits': len(read_evidence), 'proposalUnits': len(findings),
      'withoutProposedChange': len(read_evidence) - len(findings), 'assembliesAddCoverage': 0,
      'sourceOrderedClosureSha256': sha((OLD / 'evidence/closure-ids.txt').read_bytes()),
      'fullPairReadEvidenceSha256': sha(path.read_bytes()),
      'compiledProgramSha256': compiled['compiledProgramSha256'],
      'sceneGroupsInstructionSequenceInspected': 110,
      'compiledOccurrenceMissingClosureRows': sum(r['collection']=='Dialogs' and not r['compiledOccurrences'] for r in read_evidence),
      'remainingLimits': ['No game launch, final package, font/layout or progression check.',
                         'Compiled bytes describe order, not runtime reachability.',
                         'Mandatory regression catalog requires bounded source risk surface extension.',
                         'Static consumer domains are supersets; saved-game occupancy and deficit item restrictions remain unverified.'],
      'telemetry': {'model': 'inherited GPT-6 family; exact serving model not exposed', 'reasoning': 'not exposed',
                    'inputTokens': None, 'cachedInputTokens': None, 'outputTokens': None, 'totalTokens': None,
                    'status': 'per-request usage not exposed; unknown, not zero'}})
print(json.dumps({'pins': len(pins), 'fullPairReadUnits': len(read_evidence), 'proposalUnits': len(findings)}))
