#!/usr/bin/env python3
"""Repack a verified locale's table bundle while preserving its exact payload.

This diagnoses runtime decoder differences. CRC remains enabled. Existing
archives and authored strings are immutable; write a new diagnostic artifact.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import UnityPy
from UnityPy.streams import EndianBinaryReader
from addressables_catalog import bundle_crc, update_bundle
from unity_bundle_writer import repack_bytes, block_crcs
from probe_assets import ROOT, digest, require

BUNDLE='NoImNotAHuman_Data/StreamingAssets/aa/StandaloneWindows64/localization-string-tables-russian(ru)_assets_all.bundle'
CATALOG='NoImNotAHuman_Data/StreamingAssets/aa/catalog.bin'


def payload(path):
    env=UnityPy.load(str(path));reader=EndianBinaryReader(path.read_bytes())
    require(reader.read_string_to_null()=='UnityFS','Expected UnityFS')
    reader.read_u_int();reader.read_string_to_null();reader.read_string_to_null()
    directory,data=env.file.read_fs(reader)
    return directory,data.bytes


def repack(archive,output,destination,compression="lz4"):
    require(archive.is_relative_to(ROOT/'dist') and output.is_relative_to(ROOT/'outputs') and
            destination.is_relative_to(ROOT/'dist') and not output.exists() and not destination.exists(), 'Use new canonical artifacts')
    proof=json.loads(archive.with_suffix('.zip.json').read_text())
    require(digest(archive)==proof['sha256'],'Parent archive changed')
    output.mkdir(parents=True)
    with ZipFile(archive) as zipped:
        report=json.loads(zipped.read('report.json'))
        for name,row in report['artifacts'].items():
            path=output/name
            require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe package path')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(zipped.read(name))
            require(digest(path)==row['sha256'],'Parent member differs')
        report['parentArchive']=str(archive.relative_to(ROOT));report['parentArchiveSha256']=digest(archive)
    original=output/'before'/Path(BUNDLE).name;original.parent.mkdir();original.write_bytes((output/BUNDLE).read_bytes())
    directories,before=payload(original)
    env=UnityPy.load(str(original))
    expected={o.path_id:o.get_raw_data() for o in env.objects}
    raw_files={}
    for directory in directories:
        raw=EndianBinaryReader(before[directory.offset:directory.offset+directory.size]);raw.flags=directory.flags
        raw_files[directory.path]=raw
    env.file.files=raw_files
    (output/BUNDLE).write_bytes(repack_bytes(original.read_bytes()) if compression=='lz4' else env.file.save(packer='none'))
    crcs=block_crcs((output/BUNDLE).read_bytes())
    require(not crcs['ambiguousBlocks'] and crcs['logicalCrc']==crcs['runtimeBoundaryCrc'], 'Runtime compression boundary differs')
    after_dirs,after=payload(output/BUNDLE)
    require(before==after and directories==after_dirs,'Uncompressed payload changed')
    require({o.path_id:o.get_raw_data() for o in UnityPy.load(str(output/BUNDLE)).objects}==expected,'Serialized objects changed')
    new_catalog,integrity=update_bundle((output/CATALOG).read_bytes(),original,output/BUNDLE)
    (output/CATALOG).write_bytes(new_catalog)
    report['artifacts'][BUNDLE]['sha256']=digest(output/BUNDLE)
    report['artifacts'][CATALOG]['sha256']=digest(output/CATALOG)
    report['bundleCompressionRepair']={'packer':compression,'uncompressedPayloadSha256':hashlib.sha256(before).hexdigest(),
        'uncompressedPayloadByteForByteUnchanged':True,'serializedObjectsCompared':len(expected),
        'crcEnabled':True,'crc':bundle_crc(output/BUNDLE),'catalogIntegrity':integrity,
        'recipeSha256':digest(Path(__file__)),'sharedWriterSha256':digest(ROOT/'Scripts/unity_bundle_writer.py'),'runtime':'pending','blockVerification':crcs}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with ZipFile(destination,'w',ZIP_DEFLATED) as zipped:
        for name in report['artifacts']:zipped.write(output/name,name)
        zipped.write(output/'report.json','report.json')
        zipped.writestr('README.txt','Diagnostic package: exact authored payload, runtime-compatible table bundle, CRC enabled.\n')
    with ZipFile(destination) as zipped:require(zipped.testzip() is None and len(zipped.namelist())==33,'Diagnostic archive invalid')
    destination.with_suffix('.zip.json').write_text(json.dumps({'locale':report['locale'],'sha256':digest(destination),
        'parentArchiveSha256':digest(archive),'status':'Compression diagnostic; runtime pending'},indent=2)+'\n')
    print(json.dumps(report['bundleCompressionRepair']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compression',choices=['none','lz4'],default='lz4');p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    repack(a.archive.resolve(),a.output.resolve(),a.destination.resolve(),a.compression)
