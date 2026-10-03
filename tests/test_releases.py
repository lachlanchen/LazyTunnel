from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from lazytunnel_core.releases import install_release


class ReleaseTests(unittest.TestCase):
    def test_server_release_contains_all_runtime_imports(self):
        source=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('server_cli',source/'scripts/lazytunnel-server.py')
        server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            install_release(source,base,server.SERVER_FILES,'scripts/lazytunnel-server.py')
            current=base/'current'
            result=subprocess.run([sys.executable,str(current/'scripts/lazytunnel-server.py'),
                                   'update','--source',str(current)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_validation_and_failed_canary_preserve_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();base=root/'installed'
            script=source/'cli.py';script.write_text('print("working")\n')
            first=install_release(source,base,['cli.py'],'cli.py')
            script.write_text('this is invalid Python !!!')
            with self.assertRaises(SyntaxError):install_release(source,base,['cli.py'],'cli.py')
            self.assertEqual((base/'current').resolve().name,first)
            script.write_text('raise RuntimeError("bad candidate")\n')
            with self.assertRaises(ValueError):install_release(source,base,['cli.py'],'cli.py')
            self.assertEqual((base/'current').resolve().name,first)
            script.write_text('print("new version")\n')
            second=install_release(source,base,['cli.py'],'cli.py')
            self.assertEqual((base/'previous').resolve().name,first)
            self.assertEqual((base/'current').resolve().name,second)
            self.assertEqual(install_release(source,base,['cli.py'],'cli.py'),second)
            self.assertEqual((base/'previous').resolve().name,first)
            self.assertEqual(list((base/'releases').glob('.candidate-*')),[])

    def test_existing_release_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();base=root/'installed'
            (source/'cli.py').write_text('print("good")\n')
            first=install_release(source,base,['cli.py'],'cli.py')
            target=base/'releases'/first/'cli.py';target.write_text('corrupted\n')
            with self.assertRaises(ValueError):install_release(source,base,['cli.py'],'cli.py')
            self.assertEqual(target.read_text(),'corrupted\n')


if __name__=='__main__':unittest.main()
