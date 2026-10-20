#!/usr/bin/env python3
"""Real native replacement tests; game execution/UI remain separate checks."""
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=Path('/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verified_original(name, expected):
    """Read only hash-matching original bytes, including the installer's backup."""
    for candidate in (ORIGINAL/name, ORIGINAL/'VNRevival-NoHuman/originals'/name):
        if candidate.is_file() and sha(candidate)==expected:
            return candidate
    raise AssertionError(f'No verified original available: {name}')
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
def changed_upgrade(engine,payload,previous_engine,previous_payload,out):
    """Update a real previous install, including rollback and unknown edits."""
    assert not out.exists();out.mkdir(parents=True);game=out/'game';game.mkdir()
    for manifest in ['originals.tsv','game-version.tsv']:
        for line in (payload/manifest).read_text().splitlines():
            name,expected=line.split('\t');dest=game/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ORIGINAL/name,dest);assert sha(dest)==expected
    shutil.copyfile(ORIGINAL/'NoImNotAHuman_Data/boot.config',game/'NoImNotAHuman_Data/boot.config')
    invoke(previous_engine,previous_payload,game,'all')
    old=profile(previous_payload,'all');new=profile(payload,'all')
    assert all(sha(game/r[0])==r[2] for r in old)
    changed=[r for r in new if next(p[2] for p in old if p[0]==r[0])!=r[2]]
    assert len(changed)>=3, 'Must exercise changed translation, catalog and DLL'
    foreign=game/'BepInEx/plugins/OwnerMod/keep.txt';foreign.parent.mkdir(parents=True);foreign.write_text('Owner mod\n')
    target=game/changed[0][0];saved=target.read_bytes();target.write_bytes(b'Owner modification\n')
    invoke(engine,payload,game,'all','Unknown modification')
    assert target.read_bytes()==b'Owner modification\n';target.write_bytes(saved)
    boundary=next(i+1 for i,r in enumerate(new) if r[0]==changed[0][0])+1
    invoke(engine,payload,game,'all','Injected interruption',dict(os.environ,NOHUMAN_FAIL_AFTER=str(boundary)))
    assert all(sha(game/r[0])==r[2] for r in old)
    assert (game/'VNRevival-NoHuman/active.txt').read_text()=='all\n'
    result=subprocess.run([str(engine),str(payload),str(game),'all'],capture_output=True,text=True,env=dict(os.environ,NOHUMAN_CRASH_AFTER=str(boundary)))
    assert result.returncode==75
    invoke(engine,payload,game,'all',env=dict(os.environ,NOHUMAN_RECOVER_ONLY='1'))
    assert all(sha(game/r[0])==r[2] for r in old)
    invoke(engine,payload,game,'all');assert all(sha(game/r[0])==r[2] for r in new)
    invoke(engine,payload,game,'all');assert all(sha(game/r[0])==r[2] for r in new)
    assert foreign.read_text()=='Owner mod\n'
    cache=game/'VNRevival-NoHuman/payload'/sha(previous_payload/'inventory.tsv')
    for line in (previous_payload/'inventory.tsv').read_text().splitlines():
        name,expected=line.split('\t');assert sha(cache/name)==expected
    report={'oldInventorySha256':sha(previous_payload/'inventory.tsv'),'newInventorySha256':sha(payload/'inventory.tsv'),'changedFiles':len(changed),'checkedFiles':len(new),'checks':['real published install','unknown owner edit rejected','failed update rolls back prior files','fresh process continues from crashed update','changed target update succeeds','unchanged repeat','owner mod and previous cache retained'],'boundary':'Real previous and current payload reconstruction; no game runtime claim'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
def test(engine,payload,out):
    assert not out.exists();out.mkdir(parents=True);game=out/'game';game.mkdir();start=time.time();checks=[]
    bad=out/'wrong-build';(bad/'NoImNotAHuman_Data').mkdir(parents=True);(bad/'NoImNotAHuman_Data/boot.config').write_text('build-guid=wrong\n')
    invoke(engine,payload,bad,'all','Unsupported game build');assert not (bad/'VNRevival-NoHuman').exists();checks.append('Unsupported build rejected before writes')
    for line in (payload/'originals.tsv').read_text().splitlines():
        name,expected=line.split('\t');destination=game/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(verified_original(name,expected),destination);assert sha(destination)==expected
    for line in (payload/'game-version.tsv').read_text().splitlines():
        name,expected=line.split('\t');destination=game/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(verified_original(name,expected),destination);assert sha(destination)==expected
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
    p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--payload',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--upgrade-game',type=Path);p.add_argument('--previous-engine',type=Path);p.add_argument('--previous-payload',type=Path);a=p.parse_args()
    if a.previous_engine:
        assert a.previous_payload and not a.upgrade_game
        changed_upgrade(a.engine.resolve(),a.payload.resolve(),a.previous_engine.resolve(),a.previous_payload.resolve(),a.out.resolve())
    elif a.upgrade_game:upgrade(a.engine.resolve(),a.payload.resolve(),a.upgrade_game.resolve(),a.out.resolve())
    else:test(a.engine.resolve(),a.payload.resolve(),a.out.resolve())
