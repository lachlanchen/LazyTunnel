import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('novnc_idle',ROOT/'scripts/novnc-idle.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OverlayTests(unittest.TestCase):
    def test_overlay_preserves_original_and_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'original';out=root/'idle'
            (src/'app').mkdir(parents=True)
            (src/'vnc.html').write_text('<head></head><body>Original input controls</body>')
            (src/'app/ui.js').write_text('inhibitReconnect reconnectPassword disconnect() connect(')
            before=(src/'vnc.html').read_bytes()
            revision=module.install(src,out)
            self.assertEqual(module.install(src,out),revision)
            self.assertEqual((src/'vnc.html').read_bytes(),before)
            self.assertEqual((out/'app').resolve(),src/'app')
            self.assertEqual((out/'vnc.html').read_text().count('src="novnc-idle.mjs'),1)
            (out/'novnc-idle.css').unlink()
            (out/'novnc-idle.css').symlink_to(src/'vnc.html')
            with self.assertRaises(ValueError):module.install(src,out)
            self.assertEqual((src/'vnc.html').read_bytes(),before)

    def test_refuses_unowned_or_in_place_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();out=root/'other';out.mkdir()
            with self.assertRaises(ValueError):module.install(src,src)
            with self.assertRaises(ValueError):module.install(src,out)


if __name__=='__main__':unittest.main()
