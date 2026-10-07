"""Bounded Addressables v2 binary catalog reader and bundle integrity updater.

Schema reference: official Unity Addressables 2.9.0 package,
ContentCatalogData/BinaryStorageBuffer (binary format version 2).
https://packages.unity.com/com.unity.addressables/-/com.unity.addressables-2.9.0.tgz
No substring replacement, CRC disabling, source writes or runtime interception.
"""
import struct
import zlib
import UnityPy
from UnityPy.streams import EndianBinaryReader


class Catalog:
    def __init__(self, data):
        self.data = data
        if self.values(0, 2) != (0x0DE38942, 2):
            raise ValueError('Unsupported binary catalog header/version')

    def values(self, offset, count=1):
        if offset < 0 or offset + count*4 > len(self.data):
            raise ValueError('Catalog offset out of bounds')
        return struct.unpack_from('<' + 'I'*count, self.data, offset)

    def array(self, offset, stride=4):
        length, = self.values(offset-4)
        if length % stride or offset+length > len(self.data):
            raise ValueError('Invalid catalog array')
        return range(offset, offset+length, stride)

    def string(self, offset, separator):
        if offset == 0xFFFFFFFF:
            return None
        if offset & 0x40000000:
            pieces, seen = [], set()
            while offset != 0xFFFFFFFF:
                pos = offset & 0x3FFFFFFF
                if pos in seen:
                    raise ValueError('Cyclic catalog string')
                seen.add(pos)
                part, offset = self.values(pos, 2)
                pieces.append(self.string(part, '\0'))
            return separator.join(reversed(pieces))
        pos = offset & 0x3FFFFFFF
        length, = self.values(pos-4)
        if pos+length > len(self.data):
            raise ValueError('Invalid catalog string length')
        return self.data[pos:pos+length].decode('utf-16-le' if offset & 0x80000000 else 'ascii')

    def type_name(self, offset):
        _, class_id = self.values(offset, 2)
        return self.string(class_id, '.')

    def bundles(self):
        found = {}
        keys, = self.values(8)
        for row in self.array(keys, 8):
            _, locations = self.values(row, 2)
            for item in self.array(locations):
                loc, = self.values(item)
                primary, internal, provider, deps, dep_hash, extra, type_id = self.values(loc, 7)
                if extra == 0xFFFFFFFF:
                    continue
                extra_type, extra_obj = self.values(extra, 2)
                if self.type_name(extra_type) != 'UnityEngine.ResourceManagement.ResourceProviders.AssetBundleRequestOptions':
                    continue
                hash_id, bundle_id, crc, size, common_id = self.values(extra_obj, 5)
                record = {'locationOffset': loc, 'optionsOffset': extra_obj,
                          'internalId': self.string(internal, '/'), 'primaryKey': self.string(primary, '/'),
                          'bundleName': self.string(bundle_id, '_'), 'crc': crc, 'size': size,
                          'hashBytes': self.data[hash_id:hash_id+16].hex(), 'commonOffset': common_id}
                if loc in found and found[loc] != record:
                    raise ValueError('Ambiguous location')
                found[loc] = record
        return found

    def keys(self):
        result = {}
        for row in self.array(self.values(8)[0], 8):
            key, locations = self.values(row, 2)
            type_id, body = self.values(key, 2)
            if self.type_name(type_id) != 'System.String':
                raise ValueError('Unsupported catalog key type')
            string_id, separator = self.values(body, 2)
            name = self.string(string_id, chr(separator & 0xFFFF))
            if name in result:
                raise ValueError('Duplicate catalog key')
            result[name] = {'object': key, 'type': type_id,
                            'locations': [self.values(i)[0] for i in self.array(locations)]}
        return result


class CatalogExtension:
    """Append storage; retain original locations, dependencies and key order."""
    def __init__(self, data):
        self.original = Catalog(data)
        self.data = bytearray(data)
        self.keys = self.original.keys()

    def append(self, raw, prefix=False):
        if prefix:
            self.data.extend(struct.pack('<I', len(raw)))
        offset = len(self.data)
        self.data.extend(raw)
        if offset >= 0x3FFFFFFF:
            raise ValueError('Catalog storage limit exceeded')
        return offset

    def string(self, value):
        try:
            return self.append(value.encode('ascii'), True)
        except UnicodeEncodeError:
            return self.append(value.encode('utf-16-le'), True) | 0x80000000

    def array(self, values):
        return self.append(struct.pack('<'+'I'*len(values), *values), True)

    def add(self, key, location):
        if key not in self.keys:
            string_type = next(iter(self.keys.values()))['type']
            body = self.append(struct.pack('<IHxx', self.string(key), 0))
            obj = self.append(struct.pack('<II', string_type, body))
            self.keys[key] = {'object': obj, 'type': string_type, 'locations': []}
        if location in self.keys[key]['locations']:
            raise ValueError('Duplicate key/location binding')
        self.keys[key]['locations'].append(location)

    def clone_asset(self, source_key, primary, internal, locale_code=None):
        source = self.original.keys()[source_key]['locations']
        if len(source) != 1:
            raise ValueError('Ambiguous source asset location')
        old = source[0]
        fields = list(self.original.values(old, 7))
        if fields[5] != 0xFFFFFFFF:
            raise ValueError('Expected asset location without provider options')
        fields[:2] = [self.string(primary), self.string(internal)]
        new = self.append(struct.pack('<7I', *fields))
        self.add(primary, new)
        if locale_code is None:
            self.add('Locale', new)
        else:
            self.add('Locale-'+locale_code, new)
            # Preserve shared labels (e.g. UI Preload); never reuse asset GUIDs.
            for name, record in self.original.keys().items():
                if old in record['locations'] and len(record['locations']) > 1 and name != 'Locale-ru':
                    self.add(name, new)
        return new

    def finish(self):
        rows = []
        for record in self.keys.values():
            rows.extend([record['object'], self.array(record['locations'])])
        key_offset = self.array(rows)
        struct.pack_into('<I', self.data, 8, key_offset)
        result = bytes(self.data)
        actual = Catalog(result).keys()
        if actual != self.keys:
            raise ValueError('Catalog extension did not round-trip')
        for key, record in self.original.keys().items():
            if actual[key]['locations'][:len(record['locations'])] != record['locations']:
                raise ValueError('Original catalog binding changed')
        return result


def bundle_crc(path):
    env = UnityPy.load(str(path))
    reader = EndianBinaryReader(path.read_bytes())
    if reader.read_string_to_null() != 'UnityFS':
        raise ValueError('Expected UnityFS bundle')
    reader.read_u_int(); reader.read_string_to_null(); reader.read_string_to_null()
    _, payload = env.file.read_fs(reader)
    return zlib.crc32(payload.bytes)


def update_bundle(catalog_bytes, original, replacement):
    before = Catalog(catalog_bytes).bundles()
    selected = [r for r in before.values() if r['internalId'].replace('\\', '/').split('/')[-1] == original.name]
    if len(selected) != 1:
        raise ValueError('Missing or ambiguous bundle location')
    entry = selected[0]
    if entry['crc'] != bundle_crc(original) or entry['size'] != original.stat().st_size:
        raise ValueError('Original bundle/catalog integrity mismatch')
    crc, size = bundle_crc(replacement), replacement.stat().st_size
    if not crc or size > 0xFFFFFFFF:
        raise ValueError('Invalid replacement integrity fields')
    changed = bytearray(catalog_bytes)
    pos = entry['optionsOffset']+8
    struct.pack_into('<II', changed, pos, crc, size)
    after = Catalog(bytes(changed)).bundles()
    expected = {k: dict(v) for k, v in before.items()}
    expected[entry['locationOffset']].update(crc=crc, size=size)
    if after != expected or changed[:pos] != catalog_bytes[:pos] or changed[pos+8:] != catalog_bytes[pos+8:]:
        raise ValueError('Unexpected catalog change')
    return bytes(changed), {'bundle': original.name, 'optionsOffset': entry['optionsOffset'],
                            'oldCrc': entry['crc'], 'newCrc': crc, 'oldSize': entry['size'], 'newSize': size,
                            'catalogBundleLocationsCompared': len(before), 'changedFieldSpan': [pos, pos+8]}
