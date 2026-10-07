#!/usr/bin/env python3
"""Assemble explicitly authored Russian glossary inputs; never generate wording."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'Documentation/glossary-research'
CORPUS = ROOT / 'Source/glossary-corpus-v2'

# These complete sentences are authored editorial rules, not inferred text.
AGREEMENT = {
    'male': 'Персонаж мужского пола; использовать мужское согласование, сохраняя момент раскрытия в исходной сцене.',
    'female': 'Персонаж женского пола; использовать женское согласование, сохраняя момент раскрытия в исходной сцене.',
    'mixed': 'Пара состоит из мужчины и женщины; согласование определять по конкретному участнику, для обоих сохранять множественное число.',
    'mixed-female': 'Группа из двух женщин; женское согласование для каждой, множественное число для обеих.',
    'male-wiki': 'Фанатская вики указывает мужской пол; использовать мужское согласование, не выводя пол из профессии.',
    'female-wiki': 'Фанатский источник описывает женскую роль; женское согласование относится только к этому включению.',
    'unknown': 'Пол канонически не установлен. По решению владельца сохранять исходные местоимения, число участников, действия и смену говорящего; не добавлять пол там, где его не сообщает оригинал. Нейтральные формы должны сохранять действующее лицо и смысл реплики.',
    'unknown-multiple': 'Пол отдельных участников канонически не установлен. По решению владельца сохранять исходные местоимения, число участников, действия и смену говорящего; не добавлять пол там, где его не сообщает оригинал. Нейтральные формы должны сохранять действующее лицо и смысл реплики.',
    'male-localized': 'Мужская форма официальной французской версии не устанавливает канонический пол по русскому источнику. По решению владельца сохранять исходные местоимения, число участников, действия и смену говорящего; не добавлять пол там, где его не сообщает оригинал.',
    'group': 'Индивидуальный состав и пол участников канонически не установлены. По решению владельца сохранять исходные местоимения, множественное число, действия и смену говорящего; не назначать группе или каждому её участнику выдуманный пол.',
    'animal': 'В русском источнике используются «кот» и «он»; биологический пол отдельно не установлен. Не добавлять биологические сведения.',
    'entity': 'Каноническое оформление неоднозначно: «она» в речи о Смерти и «брат» в её собственной образной речи. Сохранять формы по контексту, не назначая биологический пол.',
}

FAN_SOURCES = {
    'news-reporter': ('No, I am not a human Wiki — News Reporter', 'https://no-i-am-not-a-human.fandom.com/wiki/News_Reporter'),
    'weather-reporter': ('No, I am not a human Wiki — Weather Reporter', 'https://no-i-am-not-a-human.fandom.com/wiki/Weather_Reporter'),
    'fema-agent': ('No, I am not a human Wiki — FEMA Agent', 'https://no-i-am-not-a-human.fandom.com/wiki/FEMA_Agent'),
    'female-tv-presenter': ('No, I am not a human Wiki — CR Channel', 'https://no-i-am-not-a-human.fandom.com/wiki/CR_Channel'),
    'seductive-woman': ('No, I am not a human Wiki — Seductive Woman', 'https://no-i-am-not-a-human.fandom.com/wiki/Seductive_Woman'),
    'it-creature': ('No, I am not a human Wiki — IT', 'https://no-i-am-not-a-human.fandom.com/wiki/IT'),
}
SUPPLEMENTAL_KEYS = {
    'pale-visitor': ['line:tv_2_extra2_03d0e5d', 'line:tv_2_extra2_0ad57ac', 'line:tv_2_extra2_0e3a51a'],
    'angry-wounded-man': ['line:Anger_Asking_4_02e0c6c'],
    'wheelchair-man': ['line:WheelChair_Asking_SpecialEvent_1_022eec4', 'line:WheelChair_Asking_SpecialEvent_2_09d1e17'],
    'husband-and-wife': ['line:Couple_Asking_5_3_3_2_03967da', 'line:Couple_Asking_5_3_070700a'],
    'fema-recruitment-voice': ['line:phone_wifefema_2_1_065231a'],
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    decision = json.loads((INPUT / 'uncertainty-decision.json').read_text())
    approved_unknown_ids = set(decision['approvedScopeIds'])
    assert len(approved_unknown_ids) == len(decision['approvedScopeIds'])
    supporting_keys = json.loads((INPUT / 'supporting-keys.json').read_text())
    rows = [json.loads(line) for line in (CORPUS / 'strings.jsonl').read_text().splitlines()]
    index = {}
    for row in rows:
        if row['collection'] not in ('Dialogs', 'UI'):
            continue
        key = row['key']
        if key is None:
            continue
        assert key not in index, f'Duplicate source key: {key}'
        index[key] = row
    entries, evidence, unresolved = [], [], []
    for filename in ('characters.tsv', 'voices.tsv', 'additional-voices.tsv'):
        for number, line in enumerate((INPUT / filename).read_text().splitlines(), 1):
            columns = line.split('|')
            expected = 6 if filename == 'characters.tsv' else 5
            assert len(columns) == expected, (filename, number)
            if expected == 6:
                id_, term, gender, codes, key, description = columns
            else:
                id_, term, gender, key, description = columns
                codes = ''
            assert gender in AGREEMENT, gender
            assert key in index, key
            entries.append({'id': id_, 'priority': 'P0' if filename == 'characters.tsv' else 'P1',
                            'term': term, 'meaning': description + ' ' + AGREEMENT[gender],
                            'category': 'Персонажи' if filename == 'characters.tsv' else 'Голоса и участники сцен'})
            evidence.append({'id': id_, 'authoredInput': f'{filename}:{number}',
                             'genderEvidenceClass': gender, 'speakerCodes': codes.split(',') if codes else [],
                             'source': {k: index[key][k] for k in ('collection', 'id', 'key', 'text', 'yarnMetadata')}})
            if gender in ('unknown', 'unknown-multiple', 'male-localized', 'group') and id_ not in approved_unknown_ids:
                unresolved.append(id_)
    for number, line in enumerate((INPUT / 'concepts.tsv').read_text().splitlines(), 1):
        columns = line.split('|')
        assert len(columns) == 6, number
        id_, term, priority, category, key, meaning = columns
        assert key in index, key
        entries.append(dict(id=id_, term=term, priority=priority, category=category, meaning=meaning))
        evidence.append({'id': id_, 'authoredInput': f'concepts.tsv:{number}',
                         'source': {k: index[key][k] for k in ('collection', 'id', 'key', 'text', 'yarnMetadata')}})
    ids = [x['id'] for x in entries]
    assert len(ids) == len(set(ids))
    assert approved_unknown_ids.issubset(ids), 'Owner decision refers to absent entries'
    assert ids[0] == 'player'
    for entry in entries:
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', entry['id'])
        assert entry['priority'] in ('P0', 'P1', 'P2')
        assert all(isinstance(v, str) and v.strip() for v in entry.values())
        assert not any(ord(c) < 32 and c not in '\n\t' for c in entry['meaning'])
        if entry['id'] in FAN_SOURCES:
            entry['sourceTitle'], entry['sourceUrl'] = FAN_SOURCES[entry['id']]
    for row in evidence:
        row['supplementalSources'] = []
        keys = list(dict.fromkeys(SUPPLEMENTAL_KEYS.get(row['id'], []) + supporting_keys.get(row['id'], [])))
        for key in keys:
            assert key in index
            row['supplementalSources'].append({k: index[key][k] for k in ('collection', 'id', 'key', 'text', 'yarnMetadata')})
    return {'sourceLocale': 'ru', 'entries': entries}, evidence, unresolved

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--review', type=Path, help='Explicit manual audit record for this exact source artifact')
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT / 'Documentation/glossary-research')
    document, evidence, unresolved = build()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'glossary.json').write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    report = {'schemaVersion': 1, 'sourceLocale': 'ru', 'gameVersion': '1.3.19',
              'status': 'awaiting-full-editorial-audits' if not unresolved else 'draft-needs-research', 'entries': len(document['entries']),
              'canonicalReady': False, 'consecutiveCleanFullAudits': 0,
              'unresolvedCharacterIds': unresolved,
              'sourceCorpusSha256': sha(CORPUS / 'strings.jsonl'),
              'currentDialogsSha256': sha(CORPUS / 'current-dialogs.jsonl'),
              'extractorSha256': sha(ROOT / 'Scripts/extract_glossary_corpus.py'),
              'assemblerSha256': sha(Path(__file__)),
              'uncertaintyDecisionSha256': sha(INPUT / 'uncertainty-decision.json'),
              'supportingKeysSha256': sha(INPUT / 'supporting-keys.json'),
              'authoredInputs': {name: sha(INPUT / name) for name in
                                 ('characters.tsv', 'voices.tsv', 'additional-voices.tsv', 'concepts.tsv')},
              'glossaryFileSha256': sha(output / 'glossary.json'),
              'structuralValidation': 'passed; exact authored ID order, uniqueness, fields, nonempty text and source-key bindings',
              'editorialReview': 'pending; source-key equality is not full semantic coverage',
              'sourceSelectionLimit': 'Pinned current Dialogs including supplemental keys, UI and selected text-bearing images from level1 dependencies; legacy/demo/test excluded. Compiled ID presence does not prove every scene reachable.',
              'publication': 'not-requested; not-run', 'evidence': evidence}
    if args.review:
        review_path = args.review.resolve()
        if not review_path.is_relative_to(INPUT):
            raise ValueError('Review record must be in the canonical research directory')
        review = json.loads(review_path.read_text())
        pins = ('glossaryFileSha256', 'sourceCorpusSha256', 'currentDialogsSha256',
                'extractorSha256', 'uncertaintyDecisionSha256', 'supportingKeysSha256', 'authoredInputs')
        if any(review.get(key) != report[key] for key in pins):
            raise ValueError('Manual review does not match the exact glossary and source inputs')
        ids = [entry['id'] for entry in document['entries']]
        passes = review.get('fullEditorialAudits', [])
        if unresolved or review.get('unresolvedMaterialQuestions') or len(passes) != 2:
            raise ValueError('Manual review has unresolved questions or lacks two clean full audits')
        for audit in passes:
            if (audit.get('glossaryFileSha256') != report['glossaryFileSha256']
                    or audit.get('result') != 'clean' or audit.get('findings') != []
                    or sorted(audit.get('reviewedIds', [])) != sorted(ids)
                    or not {'term', 'meaning'}.issubset(audit.get('fieldsRead', []))):
                raise ValueError('Manual review does not record a clean full-entry reading')
        for key in ('rosterReview', 'textureReview'):
            reference = review[key]
            path = (INPUT / reference['path']).resolve()
            if not path.is_relative_to(INPUT) or sha(path) != reference['sha256']:
                raise ValueError(f'{key} evidence does not match its reviewed file')
        report.update(status='canonical-ready', canonicalReady=True, consecutiveCleanFullAudits=2,
                      editorialReview='Two explicitly recorded full-entry readings of unchanged text; see manual review record.',
                      manualReviewSha256=sha(review_path))
    (output / 'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('evidence', 'authoredInputs')}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
