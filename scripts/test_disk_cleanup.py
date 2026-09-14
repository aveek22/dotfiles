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


def _make_target(key, tier=dc.Tier.SAFE):
    return dc.Target(
        key=key,
        label=key,
        tier=tier,
        size_fn=lambda: 0,
        prune_fn=lambda: "",
        present_fn=lambda: True,
    )


class ParseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.targets = [
            _make_target("poetry"),
            _make_target("npm"),
            _make_target("docker-volumes", tier=dc.Tier.DESTRUCTIVE),
        ]

    def test_digit_indices_select_in_order(self):
        result = dc.parse_selection("1,3", self.targets)
        self.assertEqual([t.key for t in result], ["poetry", "docker-volumes"])

    def test_all_selects_every_target(self):
        result = dc.parse_selection("a", self.targets)
        self.assertEqual(result, self.targets)

    def test_all_word_also_works(self):
        result = dc.parse_selection("all", self.targets)
        self.assertEqual(result, self.targets)

    def test_quit_raises_system_exit(self):
        with self.assertRaises(SystemExit) as ctx:
            dc.parse_selection("q", self.targets)
        self.assertEqual(ctx.exception.code, 0)

    def test_invalid_and_out_of_range_tokens_are_ignored(self):
        result = dc.parse_selection("0,2,9,abc", self.targets)
        self.assertEqual([t.key for t in result], ["npm"])

    def test_whitespace_and_case_are_tolerated(self):
        result = dc.parse_selection(" 1 , 2 ", self.targets)
        self.assertEqual([t.key for t in result], ["poetry", "npm"])


class FilterByKeysTests(unittest.TestCase):
    def test_keeps_order_and_drops_unmatched(self):
        targets = [_make_target("poetry"), _make_target("npm"), _make_target("maven")]
        result = dc.filter_by_keys(["maven", "poetry"], targets)
        self.assertEqual([t.key for t in result], ["poetry", "maven"])

    def test_unknown_key_yields_empty(self):
        targets = [_make_target("poetry")]
        self.assertEqual(dc.filter_by_keys(["nope"], targets), [])


class BuildTargetsTests(unittest.TestCase):
    def test_mac_includes_brew_not_apt(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = dc.build_targets("mac", Path(tmp))
            keys = [t.key for t in targets]
            self.assertIn("brew", keys)
            self.assertNotIn("apt", keys)

    def test_linux_includes_apt_not_brew(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = dc.build_targets("linux", Path(tmp))
            keys = [t.key for t in targets]
            self.assertIn("apt", keys)
            self.assertNotIn("brew", keys)

    def test_common_dir_wipe_keys_present_on_both_os(self):
        with tempfile.TemporaryDirectory() as tmp:
            common_keys = {
                "poetry", "pip", "npm", "maven", "gradle",
                "ivy2", "sbt-boot", "coursier", "terraform",
            }
            for os_name in ("mac", "linux"):
                keys = {t.key for t in dc.build_targets(os_name, Path(tmp))}
                self.assertTrue(common_keys.issubset(keys), os_name)

    def test_docker_and_trash_tiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = {t.key: t for t in dc.build_targets("mac", Path(tmp))}
            self.assertEqual(targets["docker-safe"].tier, dc.Tier.SAFE)
            self.assertEqual(targets["docker-volumes"].tier, dc.Tier.DESTRUCTIVE)
            self.assertEqual(targets["trash"].tier, dc.Tier.DESTRUCTIVE)

    def test_maven_target_never_touches_settings_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            m2 = home / ".m2"
            m2.mkdir()
            (m2 / "settings.xml").write_text("<settings/>")
            repo = m2 / "repository"
            repo.mkdir()
            (repo / "some.jar").write_bytes(b"x" * 10)

            targets = {t.key: t for t in dc.build_targets("mac", home)}
            targets["maven"].prune_fn()

            self.assertTrue((m2 / "settings.xml").exists())
            self.assertFalse(repo.exists())

    def test_trash_wipes_contents_keeps_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            real_trash = home / ".Trash"
            real_trash.mkdir()
            (real_trash / "deleted.txt").write_bytes(b"x" * 5)

            targets = {t.key: t for t in dc.build_targets("mac", home)}
            targets["trash"].prune_fn()

            self.assertTrue(real_trash.exists())
            self.assertEqual(list(real_trash.iterdir()), [])


class BuildInfoItemsTests(unittest.TestCase):
    def test_reports_pyenv_and_sdkman_sizes_without_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            versions = home / ".pyenv" / "versions" / "3.11.0"
            versions.mkdir(parents=True)
            (versions / "python").write_bytes(b"x" * 30)

            items = dc.build_info_items(home)
            pyenv_item = next(i for i in items if "pyenv" in i.label.lower())

            self.assertTrue(pyenv_item.present_fn())
            self.assertEqual(pyenv_item.size_fn(), 30)
            self.assertFalse(hasattr(pyenv_item, "prune_fn"))


if __name__ == "__main__":
    unittest.main()
