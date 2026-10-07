"""Exercise the real file boundary; replace only process inventory and one copy failure."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
import install_locale_probe as installer
from probe_assets import ROOT,digest


class InstallBoundaryTests(unittest.TestCase):
    def test_failure_between_files_keeps_unverified_receipt_and_backups(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as directory:
            folder=Path(directory);fixture=folder/'fixture';game=fixture/'game';build=folder/'build';output=folder/'receipt'
            game.mkdir(parents=True);build.mkdir()
            artifacts={};prior=[]
            for name in ['first','second']:
                (game/name).write_text('old '+name);(build/name).write_text('new '+name)
                artifacts[name]={'sha256':digest(build/name)}
                prior.append({'relativePath':name,'after':digest(game/name)})
            (build/'report.json').write_text(json.dumps({'artifacts':artifacts}))
            previous=folder/'previous.json';previous.write_text(json.dumps({'files':prior}))
            original_copy=installer.shutil.copy2
            def fail_second_source(source,destination):
                if Path(source)==build/'second':raise OSError('injected second replacement failure')
                return original_copy(source,destination)
            with patch.object(installer,'FIXTURE',fixture),patch.object(installer,'GAME',game), \
                 patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='')), \
                 patch.object(installer.shutil,'copy2',side_effect=fail_second_source):
                with self.assertRaisesRegex(OSError,'injected second replacement failure'):
                    installer.install(build,previous,output)
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertFalse(receipt['allInstalledHashesVerified'])
            self.assertEqual((game/'first').read_text(),'new first')
            self.assertEqual((game/'second').read_text(),'old second')
            for name in ['first','second']:self.assertEqual((output/name).read_text(),'old '+name)
            # The same mechanism succeeds when only the injected failure is removed.
            restore=folder/'mixed-state.json'
            restore.write_text(json.dumps({'files':[{'relativePath':n,'after':digest(game/n)} for n in artifacts]}))
            with patch.object(installer,'FIXTURE',fixture),patch.object(installer,'GAME',game), \
                 patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='')):
                installer.install(build,restore,folder/'positive')
            self.assertTrue(json.loads((folder/'positive/receipt.json').read_text())['allInstalledHashesVerified'])
            for name in artifacts:self.assertEqual(digest(game/name),artifacts[name]['sha256'])


if __name__=='__main__':unittest.main()
