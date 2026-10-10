"""Version 2: use operand wire types from the saved program, retaining fields.

Version 1 was a failed probe with wrong operand field assumptions and is preserved.
"""
import read_compiled_context as context
import json
import struct
import sys


def operand(data):
    values = list(context.fields(data))
    assert len(values) == 1, values
    field, wire, value = values[0]
    if wire == 2:
        return value.decode('utf-8')
    if wire == 5:
        return struct.unpack('<f', value)[0]
    if wire == 0:
        return bool(value)
    raise ValueError(values)


context.operand = operand
nodes, program_hash = context.load()
root = context.ROOT
source = {r['key']: r['text'] for r in (json.loads(line) for line in (root / 'Source/glossary-corpus-v2/current-dialogs.jsonl').read_text().splitlines())}
closure = {r['key']: r for r in (json.loads(line) for line in (root / 'Translations/sw/semantic-correction-cycle-01/closure-ids-v2.jsonl').read_text().splitlines()) if r['collection'] == 'Dialogs'}
print('Program SHA256:', program_hash)
for name in sys.argv[1:]:
    print('NODE:', name)
    for instruction in nodes[name]:
        print(instruction)
        for argument in instruction['operands']:
            if isinstance(argument, str) and argument.startswith('line:'):
                print(source.get(argument, '[not in current corpus]'), '=>', closure.get(argument, {}).get('target', '[outside closure]'))
