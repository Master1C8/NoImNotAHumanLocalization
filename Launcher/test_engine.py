#!/usr/bin/env python3
"""Real native replacement tests; game execution/UI remain separate checks."""
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def profile(payload,locale):
    return [line.split('\t') for line in (payload/'profiles'/f'{locale}.tsv').read_text().splitlines()]
def invoke(engine,payload,game,locale,expect=None,env=None):
    result=subprocess.run([str(engine),str(payload),str(game),locale],capture_output=True,text=True,env=env)
    if expect is None:assert result.returncode==0,(locale,result.stderr)
    else:assert result.returncode!=0 and expect in result.stderr,(expect,result)
    return result
def upgrade(engine,payload,game,out):
    """Exercise compression-only upgrade from a verified legacy flat cache."""
    assert not out.exists();out.mkdir(parents=True)
    rows=profile(payload,'all');cache=game/'VNRevival-NoHuman';legacy=cache/'payload'
    assert (cache/'owner.txt').read_text()=='fun.vnrevival.nohuman.launcher/0.2.0\n'
    assert (legacy/'chunks.bin').is_file() and (legacy/'profiles/all.tsv').is_file()
    before={str(p.relative_to(legacy)):sha(p) for p in legacy.rglob('*') if p.is_file()}
    assert all(sha(game/r[0])==r[2] for r in rows), 'Upgrade requires matching old/new reconstructed bytes'
    invoke(engine,payload,game,'all')
    assert all(sha(legacy/name)==expected for name,expected in before.items())
    version=legacy/sha(payload/'inventory.tsv')
    for line in (payload/'inventory.tsv').read_text().splitlines():
        name,expected=line.split('\t');assert sha(version/name)==expected
    assert all(sha(game/r[0])==r[2] for r in rows)
    report={'nativeEngineSha256':sha(engine),'payloadInventorySha256':sha(payload/'inventory.tsv'),
            'legacyCacheFilesPreserved':len(before),'installedFilesVerified':len(rows),
            'boundary':'Real compression-only cache upgrade; identical target bytes, separate inventory-hash namespace, legacy cache retained.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
def test(engine,payload,out):
    assert not out.exists();out.mkdir(parents=True);game=out/'game';game.mkdir();start=time.time();checks=[]
    bad=out/'wrong-build';(bad/'NoImNotAHuman_Data').mkdir(parents=True);(bad/'NoImNotAHuman_Data/boot.config').write_text('build-guid=wrong\n')
    invoke(engine,payload,bad,'all','Unsupported game build');assert not (bad/'VNRevival-NoHuman').exists();checks.append('Unsupported build rejected before writes')
    for line in (payload/'originals.tsv').read_text().splitlines():
        name,expected=line.split('\t');destination=game/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ORIGINAL/name,destination);assert sha(destination)==expected
    for line in (payload/'game-version.tsv').read_text().splitlines():
        name,expected=line.split('\t');destination=game/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ORIGINAL/name,destination);assert sha(destination)==expected
    shutil.copyfile(ORIGINAL/'NoImNotAHuman_Data/boot.config',game/'NoImNotAHuman_Data/boot.config')
    code=game/'GameAssembly.dll'
    with code.open('r+b') as f: original_byte=f.read(1);f.seek(0);f.write(bytes([original_byte[0]^1]))
    invoke(engine,payload,game,'all','Game code or metadata differs')
    assert not (game/'VNRevival-NoHuman').exists()
    with code.open('r+b') as f:f.write(original_byte)
    checks.append('Changed game code rejected before writes; matching positive control uses the same restored build')
    foreign=game/'BepInEx/plugins/OwnerMod/keep.txt';foreign.parent.mkdir(parents=True);foreign.write_text('Owner unrelated mod\n')
    # A foreign DLL satisfies earlier build/payload guards but fails ownership.
    dll=game/'winhttp.dll';dll.write_text('Owner proxy DLL\n');before=sha(dll)
    invoke(engine,payload,game,'all','Unknown modification');assert sha(dll)==before;dll.unlink();checks.append('Foreign proxy DLL protected at ownership boundary')
    rows=profile(payload,'all');assert len(rows)==410
    originals={r[0]:sha(game/r[0]) for r in rows if r[1]!='-'}
    boundary=next(i+1 for i,r in enumerate(rows) if r[1]!='-')+2
    env=os.environ.copy();env['NOHUMAN_FAIL_AFTER']=str(boundary)
    invoke(engine,payload,game,'all','Injected interruption',env)
    assert all(sha(game/name)==expected for name,expected in originals.items())
    assert all(not (game/r[0]).exists() for r in rows if r[1]=='-')
    assert not (game/'VNRevival-NoHuman/active.txt').exists()
    checks.append('Failure between real original-resource promotions restores originals and removes newly created files')
    env=os.environ.copy();env['NOHUMAN_CRASH_AFTER']=str(boundary)
    result=subprocess.run([str(engine),str(payload),str(game),'all'],env=env,capture_output=True,text=True)
    assert result.returncode==75 and (game/'VNRevival-NoHuman/transaction.tsv').exists()
    env=os.environ.copy();env['NOHUMAN_RECOVER_ONLY']='1'
    invoke(engine,payload,game,'all',env=env)
    assert all(sha(game/name)==expected for name,expected in originals.items())
    assert all(not (game/r[0]).exists() for r in rows if r[1]=='-')
    assert not (game/'VNRevival-NoHuman/active.txt').exists()
    assert not (game/'VNRevival-NoHuman/transaction.tsv').exists()
    checks.append('New process recovers journal after abrupt exit; original state verified before retry')
    invoke(engine,payload,game,'all')
    for name,base,expected,size,refs in rows:assert sha(game/name)==expected and (game/name).stat().st_size==int(size),name
    assert (game/'VNRevival-NoHuman/active.txt').read_text()=='all\n'
    checks.append('All 410 simultaneous-language files match pinned payload after first installation')
    invoke(engine,payload,game,'all');assert all(sha(game/r[0])==r[2] for r in rows)
    checks.append('Unchanged repeat preserves already verified postcondition')
    assert foreign.read_text()=='Owner unrelated mod\n';checks.append('Unrelated mod retained')
    locales=[line.split('\t')[0] for line in (payload/'locales.tsv').read_text().splitlines()]
    corrupted=out/'bad-payload';shutil.copytree(payload,corrupted)
    with (corrupted/'chunks.bin').open('r+b') as f:f.seek(50);byte=f.read(1);f.seek(50);f.write(bytes([byte[0]^1]))
    invoke(engine,corrupted,game,'all','Payload verification failed');checks.append('Corrupt chunk rejected by pinned payload inventory')
    (corrupted/'inventory.tsv').write_text('modified inventory\n');invoke(engine,corrupted,game,'all','Payload inventory differs');checks.append('Changed inventory rejected by binary pin')
    report={'nativeEngineSha256':sha(engine),'payloadInventorySha256':sha(payload/'inventory.tsv'),'locales':locales,'installedFiles':410,'checks':checks,'seconds':round(time.time()-start,2),'boundary':'Real file reconstruction, ownership and transactional replacement. No game/UI execution is mocked or claimed.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--payload',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--upgrade-game',type=Path);a=p.parse_args()
    if a.upgrade_game:upgrade(a.engine.resolve(),a.payload.resolve(),a.upgrade_game.resolve(),a.out.resolve())
    else:test(a.engine.resolve(),a.payload.resolve(),a.out.resolve())
