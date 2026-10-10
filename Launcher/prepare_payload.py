#!/usr/bin/env python3
"""Package exact reviewed profiles with content-addressed, compressed chunks."""
import argparse, ctypes, hashlib, json, re, struct, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'runtime/No Human Probe.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human'
ORIGINAL = Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human')
NAMES = {'th':'Thai','id':'Indonesian','cs':'Czech','hu':'Hungarian','nl':'Dutch','fa':'Persian','ro':'Romanian','hi':'Hindi','fil':'Filipino','el':'Greek','bg':'Bulgarian','sr':'Serbian','sw':'Swahili','he':'Hebrew'}
ANCHOR = re.compile(rb'\x37[\x00-\x0f]')
def sha(data): return hashlib.sha256(data).hexdigest()
def chunks(data):
    start = 0
    for m in ANCHOR.finditer(data):
        end = m.end()
        while end - start > 32768:
            yield data[start:start+32768]; start += 32768
        if end - start >= 4096:
            yield data[start:end]; start = end
    while len(data)-start > 32768:
        yield data[start:start+32768]; start += 32768
    if start < len(data): yield data[start:]

def compressor():
    lib=ctypes.CDLL('/opt/homebrew/lib/libzstd.dylib')
    lib.ZSTD_versionString.restype=ctypes.c_char_p
    assert lib.ZSTD_versionString()==b'1.5.7', 'Use the pinned Zstandard 1.5.7 compressor'
    lib.ZSTD_compressBound.argtypes=[ctypes.c_size_t];lib.ZSTD_compressBound.restype=ctypes.c_size_t
    lib.ZSTD_compress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];lib.ZSTD_compress.restype=ctypes.c_size_t
    lib.ZSTD_isError.argtypes=[ctypes.c_size_t];lib.ZSTD_isError.restype=ctypes.c_uint
    def compress(part):
        encoded=ctypes.create_string_buffer(lib.ZSTD_compressBound(len(part)))
        n=lib.ZSTD_compress(encoded,len(encoded),part,len(part),19)
        assert not lib.ZSTD_isError(n) and n<=270336, 'Bounded Zstandard compression failed'
        return encoded.raw[:n]
    return compress

def build(out):
    assert not out.exists(), 'Preserve previous payload'
    out.mkdir(parents=True); (out/'profiles').mkdir()
    combined=ROOT/'outputs/launcher-combined-v4'
    report=json.loads((combined/'report.json').read_text())
    assert report['mode']=='all-native' and report['nativeLocales']==32 and set(report['locales'])==set(NAMES)
    assert len(report['artifacts'])==31 and report['staticEntries']==178
    files={name:(combined/name).read_bytes() for name in report['artifacts']}
    assert all(sha(files[n])==a['sha256'] for n,a in report['artifacts'].items())
    loader=json.loads((ROOT/'outputs/runtime-loader-install-v1/receipt.json').read_text())
    for row in loader['files']:
        data=(GAME/row['relativePath']).read_bytes();assert sha(data)==row['sha256'];files[row['relativePath']]=data
    # Generated interop is bound to the exact unmodified game code/metadata.
    # Bundle the verified cache so first launch does not depend on downloading
    # or regenerating support assemblies in a player's Wine prefix.
    game_version={}
    for name in ['GameAssembly.dll','NoImNotAHuman_Data/il2cpp_data/Metadata/global-metadata.dat']:
        expected=sha((ORIGINAL/name).read_bytes());assert sha((GAME/name).read_bytes())==expected;game_version[name]=expected
    cache_pins={}
    for directory in ['BepInEx/interop']:
        for p in sorted((GAME/directory).rglob('*')):
            if p.is_file():
                name=str(p.relative_to(GAME));data=p.read_bytes();files[name]=data;cache_pins[name]=sha(data)
    assert len(cache_pins)==145
    # Match BE.788 ComputeHash without generation-only Unity base libraries.
    # Both generator assemblies are themselves pinned by the loader receipt.
    interop_hash=hashlib.md5((GAME/'GameAssembly.dll').read_bytes()+b'1.5.3.0'+b'2022.1.0.0').hexdigest()
    files['BepInEx/interop/assembly-hash.txt']=interop_hash.encode()
    files['BepInEx/config/BepInEx.cfg']=b'[Logging.Console]\nEnabled = false\n[Logging.Disk]\nEnabled = true\n[IL2CPP]\nUpdateInteropAssemblies = false\nUnityBaseLibrariesSource = \n'
    module=ROOT/'outputs/launcher-native-languages-v3/bin/NoHuman.NativeLanguages.dll'
    files['BepInEx/plugins/NoHuman.NativeLanguages/NoHuman.NativeLanguages.dll']=module.read_bytes()
    text=(combined/'static-text.json').read_bytes();assert sha(text)==report['staticTextSha256']
    files['BepInEx/plugins/NoHuman.NativeLanguages/static-text.json']=text
    renderer=ROOT/'outputs/launcher-renderer-v1';rr=json.loads((renderer/'receipt.json').read_text())
    binary=(renderer/'bin/net6.0/NoHuman.TextRenderer.dll').read_bytes();assert sha(binary)==rr['binarySha256']
    files['BepInEx/plugins/NoHuman.TextRenderer/NoHuman.TextRenderer.dll']=binary
    pins=json.loads((ROOT/'Resources/VisualQA/capture-renderer-v1.json').read_text())['pluginFiles']
    for name in ['BepInEx/plugins/NoHuman.TextRenderer/hi-source.ttf','BepInEx/plugins/NoHuman.TextRenderer/libHarfBuzzSharp.dll']:
        data=(GAME/name).read_bytes();assert sha(data)==pins[name];files[name]=data
    assert len(files)==410
    base_chunks={};base_hashes={}
    for name in sorted(report['artifacts']):
        data=(ORIGINAL/name).read_bytes();base_hashes[name]=sha(data);offset=0
        for part in chunks(data):
            base_chunks.setdefault(sha(part),(name,offset,len(part)));offset+=len(part)
    encode=compressor()
    blobs=[];blob_ids={};lines=[];total=0
    with (out/'chunks.bin').open('xb') as stream:
        for name,data in sorted(files.items()):
            assert '\t' not in name and '\n' not in name and not Path(name).is_absolute() and '..' not in Path(name).parts
            baseline=base_hashes.get(name,'-');assert not (ORIGINAL/name).exists() or name in base_hashes
            refs=[]
            parts=(data[i:i+262144] for i in range(0,len(data),262144)) if name not in base_hashes else chunks(data)
            for part in parts:
                key=sha(part)
                if key not in blob_ids:
                    blob_ids[key]=len(blobs)
                    if key in base_chunks:
                        base_name,offset,size=base_chunks[key];blobs.append((key,offset,0,size,base_name))
                    else:
                        encoded=encode(part);blobs.append((key,stream.tell(),len(encoded),len(part),'-'));stream.write(encoded)
                refs.append(str(blob_ids[key]))
            lines.append('\t'.join([name,baseline,sha(data),str(len(data)),','.join(refs)]));total+=len(data)
    (out/'profiles/all.tsv').write_text('\n'.join(lines)+'\n')
    (out/'blobs.tsv').write_text(''.join('\t'.join(map(str,b))+'\n' for b in blobs))
    (out/'originals.tsv').write_text(''.join(name+'\t'+expected+'\n' for name,expected in base_hashes.items()))
    (out/'locales.tsv').write_text(''.join(loc+'\t'+NAMES[loc]+'\n' for loc in NAMES))
    (out/'game-version.tsv').write_text(''.join(name+'\t'+expected+'\n' for name,expected in game_version.items()))
    assert all(sha((GAME/name).read_bytes())==expected for name,expected in cache_pins.items()), 'Interop checkpoint changed during packaging'
    assert all(sha((ORIGINAL/name).read_bytes())==expected for name,expected in base_hashes.items())
    receipt={'schemaVersion':2,'compression':'zstandard-1.5.7-level-19','version':'0.2.0','mode':'all-native','baseProject':'StardewTranslationInstaller','baseRevision':'d4154ff15c7c27c801d197750db36c39bc460aa8','reviewedProfiles':report['reviewedProfiles'],'combinedReportSha256':sha((combined/'report.json').read_bytes()),'rendererVersion':'0.3.4','nativeLocales':32,'staticEntries':178,'files':len(files),'logicalBytes':total,'compressedChunkBytes':(out/'chunks.bin').stat().st_size,'chunkCount':len(blobs),'gameVersion':'1.3.19','buildGuid':'c003ddc7de634775a85305fef3b9a0d3','gameCodePins':game_version,'interopCacheFiles':len(cache_pins),'interopAssemblyHash':interop_hash,'interopHashAlgorithm':'BE.788 ComputeHash; GameAssembly + generator 1.5.3.0 + Cpp2IL 2022.1.0.0, no generation-only base libraries','scope':'All 14 frozen reviewed translations installed simultaneously; selection/persistence in native game settings. Subsequent Foreigner/radio mechanics changes excluded.'}
    (out/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'inventory.tsv').write_text(''.join(str(p.relative_to(out))+'\t'+sha(p.read_bytes())+'\n' for p in sorted(out.rglob('*')) if p.is_file()))
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); a=p.parse_args();build(a.output.resolve())
