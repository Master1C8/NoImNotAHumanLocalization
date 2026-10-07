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
    'male': 'Мужская персона; использовать мужское согласование, сохраняя момент раскрытия в исходной сцене.',
    'female': 'Женская персона; использовать женское согласование, сохраняя момент раскрытия в исходной сцене.',
    'mixed': 'Пара состоит из мужчины и женщины; согласование определять по конкретному участнику, для обоих сохранять множественное число.',
    'mixed-female': 'Группа из двух женщин; женское согласование для каждой, множественное число для обеих.',
    'male-wiki': 'Фанатская вики указывает мужской пол; использовать мужское согласование, не выводя пол из профессии.',
    'female-wiki': 'Фанатский источник описывает женскую роль; женское согласование относится только к этому включению.',
    'unknown': 'Пол не установлен; карточка требует дополнительного исследования перед переводом.',
    'unknown-multiple': 'Пол отдельных участников не установлен; требуется дополнительное исследование и сохранение границ говорящих.',
    'male-localized': 'Мужское оформление найдено в официальной французской локализации, но не установлено русским источником; требуется дополнительное исследование.',
    'group': 'Состав и пол отдельных участников не установлены; сохранять множественное число, персональные сведения требуют дополнительного исследования.',
    'animal': 'В русском источнике используются «кот» и «он»; биологический пол отдельно не установлен. Не добавлять биологические сведения.',
    'entity': 'Каноническое оформление неоднозначно: «она» в речи о Смерти и «брат» в её собственной образной речи. Сохранять формы по контексту, не назначая биологический пол.',
}

FAN_SOURCES = {
    'news-reporter': ('No, I am not a human Wiki — News Reporter', 'https://no-i-am-not-a-human.fandom.com/wiki/News_Reporter'),
    'weather-reporter': ('No, I am not a human Wiki — Weather Reporter', 'https://no-i-am-not-a-human.fandom.com/wiki/Weather_Reporter'),
    'fema-agent': ('No, I am not a human Wiki — FEMA Agent', 'https://no-i-am-not-a-human.fandom.com/wiki/FEMA_Agent'),
    'female-tv-presenter': ('No, I am not a human Wiki — CR Channel', 'https://no-i-am-not-a-human.fandom.com/wiki/CR_Channel'),
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
            if gender in ('unknown', 'unknown-multiple', 'male-localized', 'group'):
                unresolved.append(id_)
            if id_ in ('female-tv-presenter', 'radio-believe-host'):
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
        for key in SUPPLEMENTAL_KEYS.get(row['id'], []):
            assert key in index
            row['supplementalSources'].append({k: index[key][k] for k in ('collection', 'id', 'key', 'text', 'yarnMetadata')})
    return {'sourceLocale': 'ru', 'entries': entries}, evidence, unresolved

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT / 'Documentation/glossary-research')
    document, evidence, unresolved = build()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'glossary.json').write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    report = {'schemaVersion': 1, 'sourceLocale': 'ru', 'gameVersion': '1.3.19',
              'status': 'draft-needs-research', 'entries': len(document['entries']),
              'canonicalReady': False, 'consecutiveCleanFullAudits': 0,
              'unresolvedCharacterIds': unresolved,
              'sourceCorpusSha256': sha(CORPUS / 'strings.jsonl'),
              'currentDialogsSha256': sha(CORPUS / 'current-dialogs.jsonl'),
              'extractorSha256': sha(ROOT / 'Scripts/extract_glossary_corpus.py'),
              'assemblerSha256': sha(Path(__file__)),
              'authoredInputs': {name: sha(INPUT / name) for name in
                                 ('characters.tsv', 'voices.tsv', 'additional-voices.tsv', 'concepts.tsv')},
              'glossaryFileSha256': sha(output / 'glossary.json'),
              'structuralValidation': 'passed; exact authored ID order, uniqueness, fields, nonempty text and source-key bindings',
              'editorialReview': 'pending; source-key equality is not full semantic coverage',
              'sourceSelectionLimit': 'Current Dialogs and UI; legacy/demo/test excluded. Speaking roster and texture text require final reconciliation.',
              'publication': 'not-requested; not-run', 'evidence': evidence}
    (output / 'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('evidence', 'authoredInputs')}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
