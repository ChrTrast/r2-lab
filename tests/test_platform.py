"""Έλεγχοι για Linux και Windows: φάκελος αποθήκευσης, scripts, συμβατότητα Python."""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import paths  # noqa: E402

LINUX_FILES = ["install.sh", "uninstall.sh", "start.sh", "r2-lab.desktop"]


class UserDirTests(unittest.TestCase):
    def test_linux_uses_config_folder(self):
        with mock.patch.object(paths.sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/cfg"}):
            self.assertEqual(paths.user_dir(), Path("/tmp/cfg") / "r2-lab")
        with mock.patch.object(paths.sys, "platform", "linux"), mock.patch.dict(os.environ, clear=True), \
                mock.patch.object(paths.Path, "home", return_value=Path("/home/maria")):
            self.assertEqual(paths.user_dir(), Path("/home/maria/.config/r2-lab"))

    def test_windows_uses_appdata(self):
        with mock.patch.object(paths.sys, "platform", "win32"), \
                mock.patch.dict(os.environ, {"APPDATA": r"C:\Users\x\AppData\Roaming"}):
            self.assertEqual(paths.user_dir(), Path(r"C:\Users\x\AppData\Roaming") / "r2-lab")

    def test_old_files_move_to_user_folder(self):
        with tempfile.TemporaryDirectory() as code, tempfile.TemporaryDirectory() as home:
            Path(code, "cubes_patterns.json").write_text('[{"name": "x"}]', encoding="utf-8")
            target = Path(home, "r2-lab")
            self.assertEqual(paths.prepare(code, target), target)
            self.assertEqual(Path(target, "cubes_patterns.json").read_text(encoding="utf-8"), '[{"name": "x"}]')
            self.assertFalse(Path(code, "cubes_patterns.json").exists())


class FileTests(unittest.TestCase):
    def test_linux_files_have_unix_line_endings(self):
        for name in LINUX_FILES:
            with self.subTest(file=name):
                self.assertNotIn(b"\r\n", (ROOT / name).read_bytes())

    def test_scripts_parse_with_bash(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not found")
        for name in ("install.sh", "uninstall.sh", "start.sh"):
            with self.subTest(script=name):
                result = subprocess.run([bash, "-n", str(ROOT / name)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_code_runs_on_ubuntu_python(self):
        """Ubuntu 22.04 έχει Python 3.10 και 24.04 την 3.12."""
        for f in ROOT.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            for minor in (10, 12):
                with self.subTest(file=str(f.relative_to(ROOT)), python=f"3.{minor}"):
                    ast.parse(f.read_text(encoding="utf-8"), feature_version=(3, minor))

    def test_zip_keeps_scripts_executable(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import package
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            out = package.build(os.path.join(d, "r2-lab.zip"))
            with zipfile.ZipFile(out) as z:
                info = {i.filename: i for i in z.infolist()}
        self.assertEqual((info["r2-lab/install.sh"].external_attr >> 16) & 0o777, 0o755)
        self.assertEqual((info["r2-lab/README.md"].external_attr >> 16) & 0o777, 0o644)
        for needed in ("main.py", "start.bat", "assets/r2-lab.png", "games/cubes/logic.py"):
            self.assertIn("r2-lab/" + needed, info)
        self.assertFalse(any("__pycache__" in n or n.endswith("progress.json") for n in info))

    def test_installer_copies_what_the_game_needs(self):
        script = (ROOT / "install.sh").read_text(encoding="utf-8")
        for needed in ("core", "games", "assets", "main.py", "r2-lab.desktop", "assets/r2-lab.png"):
            self.assertIn(needed, script)
        self.assertTrue((ROOT / "assets" / "r2-lab.png").exists())

    def test_installer_removes_old_edu_games(self):
        """Το παλιό όνομα ήταν «Παιχνίδια Μάθησης» (edu-games): να μη μείνει δεύτερο εικονίδιο στο μενού."""
        script = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("apt-get remove -y edu-games", script)
        self.assertIn("/usr/share/applications/edu-games.desktop", script)

    def test_windows_build_files(self):
        bat = (ROOT / "windows" / "build_exe.bat").read_bytes()
        self.assertEqual(bat.count(b"\n"), bat.count(b"\r\n"), "build_exe.bat: γραμμές CRLF")
        self.assertEqual(bat.count(b"\r"), bat.count(b"\r\n"), "build_exe.bat: σκέτο CR μέσα σε γραμμή")
        for needed in (b"--name R2Lab", b"assets\\r2-lab.ico", b"windows\\r2_lab.iss", b"R2-Lab-Setup-%VER%.exe"):
            self.assertIn(needed, bat)
        iss = (ROOT / "windows" / "r2_lab.iss").read_bytes()
        self.assertTrue(iss.startswith(b"\xef\xbb\xbf"), "r2_lab.iss: UTF-8 με BOM")
        for needed in ('#define AppName "Εργαστήρι R2"', r"build\windows\R2Lab", r"assets\r2-lab.ico",
                       "{{212D0711-8D40-444D-84F7-F2C3D3375A1C}"):
            self.assertIn(needed, iss.decode("utf-8-sig"))
        self.assertTrue((ROOT / "assets" / "r2-lab.ico").exists())


if __name__ == "__main__":
    unittest.main()
