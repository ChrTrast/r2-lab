"""Έλεγχοι για το πακέτο .deb (tools/make_deb.py), χωρίς dpkg: το ανοίγουμε όπως θα το άνοιγε το dpkg."""
import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_deb  # noqa: E402


def read_ar(data):
    """Τα κομμάτια ενός αρχείου ar: [(όνομα, περιεχόμενο, mode)]."""
    assert data[:8] == b"!<arch>\n", "λάθος αρχή αρχείου ar"
    pos, members = 8, []
    while pos < len(data):
        header = data[pos:pos + 60]
        assert header[58:60] == b"`\n", "λάθος τέλος επικεφαλίδας"
        name = header[:16].decode("ascii").strip().rstrip("/")
        size = int(header[48:58].decode("ascii").strip())
        mode = header[40:48].decode("ascii").strip()
        members.append((name, data[pos + 60:pos + 60 + size], mode))
        pos += 60 + size + (size % 2)
    assert pos == len(data)
    return members


class DebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            path = make_deb.build(os.path.join(d, "test.deb"))
            with open(path, "rb") as f:
                cls.members = read_ar(f.read())
        cls.control = tarfile.open(fileobj=io.BytesIO(cls.members[1][1]), mode="r:gz")
        cls.data = tarfile.open(fileobj=io.BytesIO(cls.members[2][1]), mode="r:gz")

    def control_file(self, name):
        return self.control.extractfile("./" + name).read().decode("utf-8")

    def test_ar_layout(self):
        self.assertEqual([m[0] for m in self.members], ["debian-binary", "control.tar.gz", "data.tar.gz"])
        self.assertEqual(self.members[0][1], b"2.0\n")
        self.assertTrue(all(m[2] == "100644" for m in self.members))

    def test_control_fields(self):
        fields = {}
        for line in self.control_file("control").splitlines():
            if line and not line.startswith(" "):
                key, _, value = line.partition(": ")
                fields[key] = value
        self.assertEqual(fields["Package"], "r2-lab")
        self.assertEqual(fields["Version"], make_deb.version())
        self.assertEqual(fields["Architecture"], "all")
        self.assertIn("python3-pygame", fields["Depends"])
        for key in ("Maintainer", "Description", "Installed-Size"):
            self.assertTrue(fields.get(key), key)
        self.assertTrue(self.control_file("control").endswith("\n"))

    def test_replaces_old_edu_games_package(self):
        """Το παλιό όνομα ήταν «Παιχνίδια Μάθησης» (edu-games): να μη μείνουν δύο εικονίδια στο μενού."""
        fields = dict(line.partition(": ")[::2] for line in self.control_file("control").splitlines()
                      if line and not line.startswith(" "))
        self.assertEqual(fields["Conflicts"], "edu-games")
        self.assertEqual(fields["Replaces"], "edu-games")
        preinst = self.control_file("preinst")
        self.assertIn("for name in r2-lab edu-games", preinst)
        self.assertIn("/usr/share/applications/$name.desktop", preinst)

    def test_scripts_are_executable_shell_with_unix_lines(self):
        for name in ("preinst", "postinst", "prerm"):
            info = self.control.getmember("./" + name)
            self.assertEqual(info.mode, 0o755, name)
            text = self.control_file(name)
            self.assertTrue(text.startswith("#!/bin/sh\n"), name)
            self.assertNotIn("\r", text, name)

    def test_files_owned_by_root_with_right_modes(self):
        for info in self.data.getmembers():
            self.assertTrue(info.name == "." or info.name.startswith("./"), info.name)   # το "./" διαβάζεται "."
            self.assertEqual((info.uid, info.gid, info.uname, info.gname), (0, 0, "root", "root"), info.name)
            if info.isdir():
                self.assertEqual(info.mode, 0o755, info.name)
            elif info.name in ("./usr/bin/r2-lab", "./opt/r2-lab/main.py"):
                self.assertEqual(info.mode, 0o755, info.name)
            else:
                self.assertEqual(info.mode, 0o644, info.name)

    def test_contents(self):
        names = set(self.data.getnames())
        for needed in ("./opt/r2-lab/main.py", "./opt/r2-lab/core/app.py",
                       "./opt/r2-lab/games/cubes/robot.py", "./opt/r2-lab/games/menu.py",
                       "./usr/bin/r2-lab", "./usr/share/applications/r2-lab.desktop",
                       "./usr/share/pixmaps/r2-lab.png"):
            self.assertIn(needed, names)
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])
        self.assertFalse([n for n in names if "/tests/" in n or "/tools/" in n])
        launcher = self.data.extractfile("./usr/bin/r2-lab").read().decode()
        self.assertIn("python3 /opt/r2-lab/main.py", launcher)
        desktop = self.data.extractfile("./usr/share/applications/r2-lab.desktop").read()
        self.assertNotIn(b"\r", desktop)
        self.assertIn(b"Exec=r2-lab", desktop)

    def test_every_game_module_is_packed(self):
        from games import GAMES
        names = set(self.data.getnames())
        for game in GAMES:
            folder = game["module"].replace(".", "/")
            self.assertIn(f"./opt/r2-lab/{folder}/__init__.py", names)

    def test_md5sums_match(self):
        lines = self.control_file("md5sums").splitlines()
        files = [m for m in self.data.getmembers() if m.isfile()]
        self.assertEqual(len(lines), len(files))
        for line in lines:
            digest, name = line.split("  ", 1)
            data = self.data.extractfile("./" + name).read()
            self.assertEqual(hashlib.md5(data).hexdigest(), digest, name)


if __name__ == "__main__":
    unittest.main()
