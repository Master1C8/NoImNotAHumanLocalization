"""Present immutable source/target context from the saved program and payload.

Numeric opcodes are preserved. No fixture, game, translator or authored mutation.
This helper records presentation only; the reviewer records decisions separately.
"""
import read_compiled_context as context
import json
import struct
import hashlib
import sys
from pathlib import Path


def operand(data):
    values = list(context.fields(data))
    assert len(values) == 1
    field, wire, value = values[0]
    if wire == 2:
        return value.decode('utf-8')
    if wire == 5:
        return struct.unpack('<f', value)[0]
    if wire == 0:
        return bool(value)
    raise ValueError(values)


context.operand = operand
ROOT = context.ROOT
EVIDENCE = ROOT / 'Translations/sw/independent-review-01'
nodes, program_hash = context.load()
source = {}
for line in (ROOT / 'Source/localization-inventory-v3/strings.jsonl').read_text().splitlines():
    row = json.loads(line)
    if row['collection'] == 'Dialogs':
        assert row['key'] not in source
        source[row['key']] = row
targets = {}
manifest = json.loads((ROOT / 'Translations/sw/semantic-correction-cycle-01/final-payload-manifest.json').read_text())
by_number = {int(row['stableId'].rsplit(':', 1)[1]): row for row in source.values()}
for artifact in manifest['artifacts']:
    path = ROOT / artifact['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256']
    for row in json.loads(path.read_text())['entries']:
        if row.get('id') in by_number:
            targets[by_number[row['id']]['key']] = row['target']
closure = [json.loads(line) for line in (ROOT / 'Translations/sw/semantic-correction-cycle-01/closure-ids-v2.jsonl').read_text().splitlines()]
index = {row['key']: number for number, row in enumerate(closure) if row['collection'] == 'Dialogs'}
consumers = {}
for name, instructions in nodes.items():
    for instruction in instructions:
        for arg in instruction['operands']:
            if isinstance(arg, str) and arg.startswith('line:'):
                consumers.setdefault(arg, []).append((name, instruction['index']))


def display_node(name):
    print('NODE', name)
    for ins in nodes[name]:
        args = ins['operands']
        if ins['opcode'] in (2, 4) and args and args[0] in source:
            key = args[0]
            marker = index.get(key, 'context')
            print(f"{marker} @{ins['index']} {key}: {source[key]['source']} => {targets.get(key, '[target unavailable]')}")
            if ins['opcode'] == 4:
                print('  OPTION', repr(args[1:]))
        elif ins['opcode'] in (0, 3, 6, 10, 12, 13, 14, 16):
            print(f"  @{ins['index']} op{ins['opcode']} {args}")


if __name__ == '__main__':
    start, stop = map(int, sys.argv[1:3])
    selected = closure[start:stop]
    names = []
    orphan = []
    for row in selected:
        if row['collection'] != 'Dialogs':
            continue
        matches = consumers.get(row['key'], [])
        if not matches:
            orphan.append(row)
        for name, _ in matches:
            if name not in names:
                names.append(name)
    for name in names:
        display_node(name)
    for row in orphan:
        print('ORPHAN', index[row['key']], row['key'], row['source'], '=>', row['target'])
    presented = sorted({index[arg] for name in names for ins in nodes[name] for arg in ins['operands'] if isinstance(arg, str) and arg in index} | {index[row['key']] for row in orphan})
    print('PRESENTED_CLOSURE_INDICES', json.dumps(presented))
