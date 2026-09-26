import importlib.util
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class PosixClientTests(unittest.TestCase):
    def test_launcher_uses_installing_python_and_quotes_paths(self):
        spec = importlib.util.spec_from_file_location(
            "posix_client", ROOT / "scripts/lazytunnel-client.py")
        client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client)
        with tempfile.TemporaryDirectory(prefix="lazy client's home ") as tmp:
            home = Path(tmp)
            code = home / ".local/share/lazytunnel/client"
            interpreter = home / "Python with spaces"
            interpreter.symlink_to(sys.executable)
            with patch.object(client, "CODE", code), \
                 patch.object(Path, "home", return_value=home), \
                 patch.object(sys, "executable", str(interpreter)), \
                 patch.object(sys, "argv", ["lazytunnel", "install", "--source", str(ROOT)]):
                client.main()
            launcher = home / ".local/bin/lazytunnel"
            self.assertIn("exec " + shlex.quote(str(interpreter)), launcher.read_text())
            result = subprocess.run([str(launcher), "--help"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("prepare", result.stdout)


if __name__ == "__main__":
    unittest.main()
