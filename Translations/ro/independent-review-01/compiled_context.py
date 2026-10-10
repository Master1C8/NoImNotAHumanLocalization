"""Read the saved source program without touching the game fixture.

Opcode numbers are retained from the artifact. This is a wire decoder, not a VM;
its output preserves instruction order and operands without claiming reachability.
"""
import json
import struct
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def fields(data):
    offset = 0

    def integer():
        nonlocal offset
        value = shift = 0
        while True:
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7

    while offset < len(data):
        header = integer()
        field, wire = header >> 3, header & 7
        if wire == 0:
            value = integer()
        elif wire == 2:
            length = integer()
            value = data[offset:offset + length]
            offset += length
        elif wire in (1, 5):
            length = 8 if wire == 1 else 4
            value = data[offset:offset + length]
            offset += length
        else:
            raise ValueError((field, wire, offset))
        yield field, wire, value
    assert offset == len(data)


def operand(data):
    values = list(fields(data))
    assert len(values) == 1, values
    field, wire, value = values[0]
    if field == 1 and wire == 2:
        return value.decode('utf-8')
    if field == 3 and wire == 5:
        return struct.unpack('<f', value)[0]
    if field == 2 and wire == 0:
        return bool(value)
    raise ValueError(values)


def load():
    path = ROOT / 'Source/glossary-corpus-v2/runtime-bindings.json'
    bindings = json.loads(path.read_text())
    raw = bytes(bindings['sharedassets0.assets:2743']['compiledYarnProgram'])
    pin = json.loads((ROOT / 'Source/glossary-corpus-v2/current-dialogs-scope.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == pin['compiledProgramSha256']
    nodes = {}
    for field, wire, value in fields(raw):
        if field != 2:
            continue
        mapping = {f: v for f, w, v in fields(value)}
        name = mapping[1].decode()
        node = list(fields(mapping[2]))
        assert next(v for f, w, v in node if f == 1).decode() == name
        instructions = []
        for f, w, v in node:
            if f != 2:
                continue
            decoded = list(fields(v))
            opcode = next((a for z, w, a in decoded if z == 1), 0)
            args = [operand(a) for z, w, a in decoded if z == 2]
            instructions.append({'index': len(instructions), 'opcode': opcode, 'operands': args})
        assert name not in nodes
        nodes[name] = instructions
    return nodes, pin['compiledProgramSha256']


