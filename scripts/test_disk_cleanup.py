import platform
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import disk_cleanup as dc


class DirSizeTests(unittest.TestCase):
    def test_missing_path_is_zero(self):
        self.assertEqual(dc.dir_size(Path("/no/such/path/at/all")), 0)

    def test_sums_nested_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_bytes(b"x" * 100)
            sub = root / "sub"
            sub.mkdir()
            (sub / "b.txt").write_bytes(b"y" * 50)
            self.assertEqual(dc.dir_size(root), 150)

    def test_ignores_symlinked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real.txt"
            real.write_bytes(b"z" * 40)
            (root / "link.txt").symlink_to(real)
            # real.txt (40 bytes) counted once; the symlink itself isn't a
            # regular file's size, so total stays 40.
            self.assertEqual(dc.dir_size(root), 40)


class HumanSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(dc.human_size(500), "500B")

    def test_kilobytes(self):
        self.assertEqual(dc.human_size(2048), "2.0K")

    def test_gigabytes(self):
        self.assertEqual(dc.human_size(4_800_000_000), "4.5G")


class WipeDirContentsTests(unittest.TestCase):
    def test_missing_path_returns_zero(self):
        self.assertEqual(dc.wipe_dir_contents(Path("/no/such/path")), 0)

    def test_removes_children_keeps_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trash"
            root.mkdir()
            (root / "file.txt").write_bytes(b"a" * 10)
            child_dir = root / "childdir"
            child_dir.mkdir()
            (child_dir / "nested.txt").write_bytes(b"b" * 5)

            freed = dc.wipe_dir_contents(root)

            self.assertEqual(freed, 15)
            self.assertTrue(root.exists())
            self.assertEqual(list(root.iterdir()), [])


class CurrentOsTests(unittest.TestCase):
    def test_darwin_maps_to_mac(self):
        with mock.patch.object(platform, "system", return_value="Darwin"):
            self.assertEqual(dc.current_os(), "mac")

    def test_linux_maps_to_linux(self):
        with mock.patch.object(platform, "system", return_value="Linux"):
            self.assertEqual(dc.current_os(), "linux")

    def test_other_maps_to_other(self):
        with mock.patch.object(platform, "system", return_value="Windows"):
            self.assertEqual(dc.current_os(), "other")


class MakeDirWipeTargetTests(unittest.TestCase):
    def test_absent_path_is_not_present_and_size_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            target = dc.make_dir_wipe_target(
                "poetry", "Poetry cache", dc.Tier.SAFE, lambda: missing
            )
            self.assertFalse(target.present_fn())
            self.assertEqual(target.size_fn(), 0)

    def test_present_path_reports_size_and_prunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir()
            (cache / "file.bin").write_bytes(b"x" * 200)
            target = dc.make_dir_wipe_target(
                "poetry", "Poetry cache", dc.Tier.SAFE, lambda: cache
            )

            self.assertTrue(target.present_fn())
            self.assertEqual(target.size_fn(), 200)

            message = target.prune_fn()

            self.assertFalse(cache.exists())
            self.assertIn("200B", message)
            self.assertEqual(target.key, "poetry")
            self.assertEqual(target.tier, dc.Tier.SAFE)


if __name__ == "__main__":
    unittest.main()
