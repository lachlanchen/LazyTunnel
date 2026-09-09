import importlib.util
import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'scripts/fleet-install-posix.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class ClientAccountTests(unittest.TestCase):
    def test_refresh_removes_only_previously_recorded_exact_keys(self):
        prior='ssh-ed25519 OLD lazy-fleet-retired\n'
        manual='ssh-ed25519 OLD manually-kept\ncommand="hostname" ssh-ed25519 LIMITED manual\n'
        new='ssh-ed25519 NEW lazy-fleet-laptop\n'
        result=installer.reconcile_authorized(prior+manual,prior,new)
        self.assertEqual(result,manual+new)
        self.assertEqual(installer.reconcile_authorized(result,new,new),result)

    def test_rejected_transfer_writes_nothing_and_runs_no_commands(self):
        import os,platform,pwd
        user=pwd.getpwuid(os.getuid())
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);root=home/'.config/lazytunnel-fleet';root.mkdir(parents=True)
            (root/'bundle.json').write_text(json.dumps({'peer':{'account':'alice'}}))
            before=(root/'bundle.json').read_bytes()
            candidate=home/'candidate.json'
            candidate.write_text(json.dumps({'peer':{'account':'bob','home':str(home),
                'platform':platform.system().lower(),'user':user.pw_name},'files':{}}))
            with patch.object(installer.Path,'home',return_value=home),patch.object(installer.os,'getuid',return_value=1000),patch.object(installer.pwd,'getpwuid',return_value=user),patch.object(sys,'argv',['install',str(candidate),'--apply']),patch.object(installer.subprocess,'run') as run,patch.object(installer.subprocess,'check_output') as check:
                mask=os.umask(0o077)
                try:
                    with self.assertRaisesRegex(RuntimeError,'Account transfer'):installer.main()
                finally:os.umask(mask)
            run.assert_not_called();check.assert_not_called()
            self.assertEqual((root/'bundle.json').read_bytes(),before)
            self.assertEqual([p.name for p in root.iterdir()],['bundle.json'])
