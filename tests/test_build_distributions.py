import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "builder", Path(__file__).resolve().parents[1] / "scripts" / "build_distributions.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildTests(unittest.TestCase):
    def canonical(self, directory, extra=None, pools=None):
        paths = ["graphics/portraits/Marine1.png"] + [
            f"graphics/portraits/portrait-{color}.png"
            for color in ("red", "purple", "orange", "blue")
        ]
        if extra:
            paths.append(extra)
        if pools is None:
            pools = {
                "standard_male": paths[:1], "standard_female": paths[1:],
                "player_male": paths[:1], "player_female": paths[1:],
            }
        archive = directory / "Starlit-Faces-All-2.0.0.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("Mod/LICENSE", "CC0 notice")
            output.writestr("Mod/PORTRAIT_NOTICE.txt", "Fictional characters")
            output.writestr("Mod/unrelated.version", "preserve this file")
            output.writestr("Mod/mod_info.json", json.dumps({
                "version": "2.0.0", "id": "starlit_faces", "name": "Starlit Faces"
            }))
            output.writestr(
                "Mod/data/world/factions/player.faction",
                json.dumps({"portraits": pools}),
            )
            for path in paths:
                output.writestr("Mod/" + path, b"portrait bytes")
        return archive

    def test_partition_version_and_gender(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            canonical = self.canonical(directory)
            dist = directory / "dist"
            with contextlib.redirect_stdout(io.StringIO()):
                builder.build(canonical, dist)
            self.assertEqual(len(list(dist.glob("*.zip"))), 6)
            with zipfile.ZipFile(dist / canonical.name) as archive:
                self.assertEqual(archive.read("Mod/unrelated.version"), b"preserve this file")
                version = json.loads(archive.read("Mod/starlit_faces.version"))
                self.assertTrue(version["directDownloadURL"].endswith(
                    "Starlit-Faces-All-2.0.0.zip"
                ))
                self.assertEqual(
                    json.loads((dist / "starlit_faces.version").read_text()), version
                )
                all_pools = json.loads(archive.read(
                    "Mod/data/world/factions/player.faction"
                ))["portraits"]
                self.assertEqual(all_pools["standard_male"], all_pools["player_male"])
                self.assertEqual(all_pools["standard_female"], all_pools["player_female"])
            for color in ("Red", "Purple", "Orange", "Blue", "General"):
                with zipfile.ZipFile(dist / f"Starlit-Faces-{color}-2.0.0.zip") as archive:
                    folder = f"StarlitFaces{color}"
                    self.assertEqual(archive.read(f"{folder}/LICENSE"), b"CC0 notice")
                    self.assertEqual(
                        archive.read(f"{folder}/PORTRAIT_NOTICE.txt"), b"Fictional characters"
                    )
                    faction = json.loads(archive.read(
                        f"{folder}/data/world/factions/player.faction"
                    ))
                    gender = "standard_male" if color == "General" else "standard_female"
                    player_gender = gender.replace("standard", "player")
                    self.assertEqual(list(faction["portraits"]), [gender, player_gender])
                    paths = faction["portraits"][gender]
                    self.assertEqual(len(paths), 1)
                    self.assertEqual(faction["portraits"][player_gender], paths)
                    self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
                    self.assertEqual(archive.read(folder + "/" + paths[0]), b"portrait bytes")
                    version_name = f"starlit_faces_{color.lower()}.version"
                    version = json.loads(archive.read(f"{folder}/{version_name}"))
                    self.assertEqual(version["modVersion"], {"major": 2, "minor": 0, "patch": 0})
                    self.assertTrue(version["directDownloadURL"].endswith(
                        f"Starlit-Faces-{color}-2.0.0.zip"
                    ))
                    self.assertEqual(archive.read(
                        f"{folder}/data/config/version/version_files.csv"
                    ).decode(), f"version file\n{version_name}\n")
                    self.assertEqual(
                        json.loads((dist / version_name).read_text()), version
                    )

    def test_distinct_and_player_only_registrations_are_filtered(self):
        paths = ["graphics/portraits/Marine1.png"] + [
            f"graphics/portraits/portrait-{color}.png"
            for color in ("red", "purple", "orange", "blue")
        ]
        pools = {
            "standard_male": paths[:1], "standard_female": paths[1:3],
            "player_male": paths[:1], "player_female": paths[2:],
        }
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            canonical = self.canonical(directory, pools=pools)
            dist = directory / "dist"
            with contextlib.redirect_stdout(io.StringIO()):
                builder.build(canonical, dist)
            with zipfile.ZipFile(dist / "Starlit-Faces-Orange-2.0.0.zip") as archive:
                faction = json.loads(archive.read(
                    "StarlitFacesOrange/data/world/factions/player.faction"
                ))
                self.assertEqual(faction["portraits"], {"player_female": [paths[3]]})
                self.assertEqual(archive.read("StarlitFacesOrange/" + paths[3]), b"portrait bytes")
            with zipfile.ZipFile(dist / "Starlit-Faces-Red-2.0.0.zip") as archive:
                faction = json.loads(archive.read(
                    "StarlitFacesRed/data/world/factions/player.faction"
                ))
                self.assertEqual(faction["portraits"], {"standard_female": [paths[1]]})

    def test_invalid_player_pools_are_rejected(self):
        path = "graphics/portraits/Marine1.png"
        invalid_pools = (
            {"standard_male": [path], "player_male": "not an array"},
            {"standard_male": [path], "player_male": [path, path]},
            {"standard_male": [path], "player_female": ["graphics/portraits/../bad.png"]},
            {"standard_male": [path], "player_female": ["graphics/portraits/missing.png"]},
        )
        for pools in invalid_pools:
            with self.subTest(pools=pools), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                canonical = self.canonical(directory, pools=pools)
                with self.assertRaises(ValueError):
                    builder.build(canonical, directory / "dist")

    def test_invalid_late_group_preserves_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            canonical = self.canonical(directory, "graphics/portraits/red-blue.png")
            dist = directory / "dist"
            dist.mkdir()
            previous = dist / "Starlit-Faces-Red-2.0.0.zip"
            previous.write_bytes(b"previous build")
            with self.assertRaises(ValueError):
                builder.build(canonical, dist)
            self.assertEqual(previous.read_bytes(), b"previous build")
            self.assertEqual(len(list(dist.iterdir())), 1)

    def test_publication_failure_restores_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            canonical = self.canonical(directory)
            dist = directory / "dist"
            dist.mkdir()
            previous = dist / "Starlit-Faces-Red-2.0.0.zip"
            previous.write_bytes(b"previous build")
            original = Path.replace

            def fail_second(source, target):
                if source.name == "Starlit-Faces-Purple-2.0.0.zip":
                    raise OSError("Simulated publication failure")
                return original(source, target)

            with patch.object(Path, "replace", fail_second), self.assertRaises(OSError):
                builder.build(canonical, dist)
            self.assertEqual(previous.read_bytes(), b"previous build")
            self.assertEqual(len(list(dist.iterdir())), 1)

    def test_failed_rollback_preserves_recovery_backups(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            canonical = self.canonical(directory)
            dist = directory / "dist"
            dist.mkdir()
            previous = dist / "Starlit-Faces-Red-2.0.0.zip"
            previous.write_bytes(b"previous build")
            original = Path.replace

            def fail_publish_and_restore(source, target):
                if source.name == "Starlit-Faces-Purple-2.0.0.zip":
                    raise OSError("Simulated publication failure")
                if source.parent.name.startswith(".starlit-backups-"):
                    raise OSError("Simulated rollback failure")
                return original(source, target)

            with patch.object(Path, "replace", fail_publish_and_restore):
                with self.assertRaisesRegex(RuntimeError, "Recovery backups:"):
                    builder.build(canonical, dist)
            backups = list(dist.glob(".starlit-backups-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (backups[0] / previous.name).read_bytes(), b"previous build"
            )


if __name__ == "__main__":
    unittest.main()
