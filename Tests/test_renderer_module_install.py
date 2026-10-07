"""Exercise the actual multi-file replacement boundary with a mocked process inventory."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
import install_renderer_module as installer
from probe_assets import ROOT,digest

class ModuleInstallBoundary(unittest.TestCase):
    def test_failure_between_replacements_preserves_partial_state_and_receipt(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as temp:
            root=Path(temp);fixture=root/'fixture';game=fixture/'game';target=game/'BepInEx/plugins/NoHuman.TextRenderer';target.mkdir(parents=True)
            font=root/'font';font.mkdir();(font/'hi-source.ttf').write_bytes((ROOT/'outputs/renderer-font-v3/hi-source.ttf').read_bytes())
            (game/'font.assets').write_bytes(b'prepared-font-asset')
            (font/'receipt.json').write_text(json.dumps({'completed':True,'files':[{'path':'font.assets','afterSha256':digest(game/'font.assets')}]}))
            names=['NoHuman.TextRenderer.dll','hi-source.ttf','libHarfBuzzSharp.dll']
            for name in names:(target/name).write_bytes(('old:'+name).encode())
            old={name:digest(target/name) for name in names};prior=root/'previous.json';prior.write_text(json.dumps({'completed':True,'files':old}))
            built=root/'module.dll';built.write_bytes(b'new-module');output=root/'installation'
            original=Path.replace;seen=[]
            def fail_second(path,destination):
                seen.append(Path(destination).name)
                if len(seen)==2:raise OSError('injected second replacement failure')
                return original(path,destination)
            with patch.object(installer,'FIXTURE',fixture),patch.object(installer,'GAME',game),patch.object(installer.subprocess,'check_output',return_value=''),patch.object(Path,'replace',fail_second):
                with self.assertRaisesRegex(OSError,'injected second replacement failure'):
                    installer.install(built,font,ROOT/'outputs/renderer-dependencies-v1/harfbuzzsharp.nativeassets.win32.8.3.1.1.nupkg',prior,output)
            receipt=json.loads((output/'receipt.json').read_text());self.assertFalse(receipt['completed'])
            first,second=seen
            self.assertEqual(digest(target/first),receipt['files'][first])
            self.assertNotEqual(digest(target/first),old[first])
            for name in names:
                if name!=first:self.assertEqual(digest(target/name),old[name])
            self.assertEqual(digest(output/'before'/first),old[first])
            self.assertEqual(digest(output/'before'/second),old[second])
            self.assertTrue((target/(second+'.renderer-tmp')).exists())
