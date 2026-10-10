"""Exercise the real UnityFS boundary that made Hungarian UI tables fail CRC."""
import random
import sys
import unittest
from pathlib import Path
from zipfile import ZipFile
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from UnityPy.helpers import CompressionHelper
from unity_bundle_writer import block_crcs, contents, repack_bytes, safe_chunks

BUNDLE='NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/localization-string-tables-russian(ru)_assets_all.bundle'


class BundleWriter(unittest.TestCase):
    def test_real_hungarian_failure_matches_unity_log(self):
        with ZipFile(ROOT/'dist/NoImNotAHuman-hu-runtime-preview-v1.zip') as zipped:
            data=zipped.read(BUNDLE)
        check=block_crcs(data)
        self.assertEqual(check['logicalCrc'],0x6e45ed0a)
        self.assertEqual(check['runtimeBoundaryCrc'],0x0adc3049)
        self.assertEqual(check['ambiguousBlocks'],[{'index':69,'bytes':96,'codec':2}])
        fixed=repack_bytes(data)
        self.assertEqual(contents(fixed),contents(data))
        actual=block_crcs(fixed)
        self.assertEqual(actual['logicalCrc'],actual['runtimeBoundaryCrc'])
        self.assertEqual(actual['logicalCrc'],check['logicalCrc'])
        self.assertEqual(actual['ambiguousBlocks'],[])

    def test_size_equal_final_chunk_is_raw_with_same_payload(self):
        base=bytearray(random.Random(0).randbytes(96))
        tail=bytes(base[:60]+base[20:26]+base[66:])
        self.assertEqual(len(CompressionHelper.compress_lz4(tail)),len(tail))
        source=b'ABcd'*(131072//4)+tail
        encoded,blocks=safe_chunks(source)
        self.assertEqual(blocks[-1],(96,96,0))
        self.assertEqual(blocks[0][2]&63,2)
        offset=0;decoded=[]
        for size,stored,flags in blocks:
            raw=encoded[offset:offset+stored];offset+=stored
            decoded.append(raw if flags&63==0 else CompressionHelper.decompress_lz4(raw,size))
        self.assertEqual(b''.join(decoded),source)

    def test_compressible_and_incompressible_positive_controls(self):
        for source in [b'x'*96,random.Random(5).randbytes(96)]:
            encoded,blocks=safe_chunks(source)
            size,stored,flags=blocks[0]
            actual=encoded if flags&63==0 else CompressionHelper.decompress_lz4(encoded,size)
            self.assertEqual(actual,source)
            self.assertTrue((stored<size and flags&63==2) or (stored==size and flags&63==0))

    def test_neighboring_czech_package_preserves_contents(self):
        with ZipFile(ROOT/'dist/NoImNotAHuman-cs-runtime-preview-v1.zip') as zipped:
            source=zipped.read(BUNDLE)
        self.assertEqual(block_crcs(source)['ambiguousBlocks'],[])
        fixed=repack_bytes(source)
        self.assertEqual(contents(fixed),contents(source))
        self.assertEqual(block_crcs(fixed)['logicalCrc'],block_crcs(source)['logicalCrc'])
