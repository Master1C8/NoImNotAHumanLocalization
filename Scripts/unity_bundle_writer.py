"""UnityFS LZ4 writer with an explicit equal-size block boundary.

Unity treats a stored block whose compressed and uncompressed lengths are equal
as raw bytes. UnityPy 1.25.4 uses > instead of >= for the final chunk, which can
label a size-equal LZ4 stream as compressed. Its own decoder then round-trips the
bundle while Unity computes a different CRC. Emit raw data and flag 0 for every
size-equal block; retain compressed bytes for genuinely smaller blocks.
"""
from dataclasses import dataclass
import zlib
import UnityPy
from UnityPy.helpers import CompressionHelper
from UnityPy.streams import EndianBinaryReader, EndianBinaryWriter


@dataclass(frozen=True)
class BundleContents:
    signature: str
    version: int
    player_version: str
    engine_version: str
    directory: tuple
    data: bytes
    aligned: bool


def contents(bundle_bytes):
    env=UnityPy.load(bundle_bytes)
    r=EndianBinaryReader(bundle_bytes)
    signature=r.read_string_to_null();version=r.read_u_int()
    player=r.read_string_to_null();engine=r.read_string_to_null()
    if signature!='UnityFS':raise ValueError('Expected UnityFS bundle')
    directory,data=env.file.read_fs(r)
    rows=tuple((d.offset,d.size,d.flags,d.path) for d in directory)
    return BundleContents(signature,version,player,engine,rows,data.bytes,env.file._uses_block_alignment)


def safe_chunks(data,block_flags=2):
    compressed,blocks=CompressionHelper.chunk_based_compress(data,block_flags)
    output=bytearray();safe=[];source_offset=stored_offset=0
    for size,stored,flags in blocks:
        encoded=compressed[stored_offset:stored_offset+stored]
        original=data[source_offset:source_offset+size]
        if stored==size and flags&63:
            encoded=original;flags &= ~63
        if flags&63 in (2,3):
            decoded=CompressionHelper.decompress_lz4(encoded,size)
        elif flags&63==0:
            decoded=encoded
        else:raise ValueError('Unexpected block codec')
        if decoded!=original:raise ValueError('Chunk payload changed')
        if len(encoded)==size and flags&63:raise ValueError('Ambiguous equal-size compressed block')
        output.extend(encoded);safe.append((size,len(encoded),flags))
        stored_offset+=stored;source_offset+=size
    if source_offset!=len(data) or stored_offset!=len(compressed):raise ValueError('Incomplete chunk coverage')
    return bytes(output),safe


def repack_bytes(bundle_bytes):
    source=contents(bundle_bytes)
    data,blocks=safe_chunks(source.data)
    meta=EndianBinaryWriter(b'\0'*16);meta.write_int(len(blocks))
    for size,stored,flags in blocks:
        meta.write_u_int(size);meta.write_u_int(stored);meta.write_u_short(flags)
    meta.write_int(len(source.directory))
    for offset,size,flags,path in source.directory:
        meta.write_long(offset);meta.write_long(size);meta.write_u_int(flags);meta.write_string_to_null(path)
    uncompressed_meta=meta.bytes;encoded_meta=CompressionHelper.compress_lz4(uncompressed_meta)
    out=EndianBinaryWriter();out.write_string_to_null(source.signature);out.write_u_int(source.version)
    out.write_string_to_null(source.player_version);out.write_string_to_null(source.engine_version)
    size_offset=out.Position;out.write_long(0)
    out.write_u_int(len(encoded_meta));out.write_u_int(len(uncompressed_meta));out.write_u_int(194)
    if source.aligned:out.align_stream(16)
    out.write_bytes(data);out.write_bytes(encoded_meta)
    end=out.Position;out.Position=size_offset;out.write_long(end)
    result=out.bytes
    actual=contents(result)
    if actual!=source:raise ValueError('Repacked directory or uncompressed payload changed')
    return result


def safe_bundle_bytes(bundle):
    # Delegate serialized-file writing to UnityPy; own the compressed envelope.
    return repack_bytes(bundle.save(packer='none'))


def block_crcs(bundle_bytes):
    """Compare flag-driven decoding with Unity's size-equal raw-block boundary.

The latter is an emulator of the observed runtime boundary, not a substitute
for loading the repaired artifact in Unity itself.
"""
    r=EndianBinaryReader(bundle_bytes)
    if r.read_string_to_null()!='UnityFS':raise ValueError('Expected UnityFS')
    version=r.read_u_int();r.read_string_to_null();r.read_string_to_null()
    total=r.read_long();stored_meta=r.read_u_int();raw_meta=r.read_u_int();flags=r.read_u_int()
    if total!=len(bundle_bytes):raise ValueError('Bundle length differs')
    if version>=7:r.align_stream(16)
    start=r.Position
    r.Position=total-stored_meta if flags&128 else start
    encoded=r.read_bytes(stored_meta)
    codec=flags&63
    metadata=CompressionHelper.decompress_lz4(encoded,raw_meta) if codec in (2,3) else encoded if codec==0 else None
    if metadata is None or len(metadata)!=raw_meta:raise ValueError('Unsupported metadata codec or length')
    meta=EndianBinaryReader(metadata);meta.read_bytes(16);count=meta.read_int()
    if count<0 or count*10>len(metadata)-20:raise ValueError('Invalid block count')
    blocks=[(meta.read_u_int(),meta.read_u_int(),meta.read_u_short()) for _ in range(count)]
    r.Position=start if flags&128 else start+stored_meta
    if flags&512:r.align_stream(16)
    logical=runtime=0;ambiguous=[]
    for i,(size,stored,block_flags) in enumerate(blocks):
        encoded=r.read_bytes(stored);codec=block_flags&63
        decoded=CompressionHelper.decompress_lz4(encoded,size) if codec in (2,3) else encoded if codec==0 else None
        if decoded is None or len(decoded)!=size:raise ValueError('Unsupported block codec or length')
        engine=encoded if size==stored else decoded
        logical=zlib.crc32(decoded,logical);runtime=zlib.crc32(engine,runtime)
        if size==stored and codec:ambiguous.append({'index':i,'bytes':size,'codec':codec})
    return {'logicalCrc':logical,'runtimeBoundaryCrc':runtime,'ambiguousBlocks':ambiguous,'blockCount':count}
