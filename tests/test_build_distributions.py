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
    def canonical(self, directory, extra=None):
        paths = ["graphics/portraits/Marine1.png"] + [
            f"graphics/portraits/portrait-{color}.png"
            for color in ("red", "purple", "orange", "blue")
        ]
        if extra:
            paths.append(extra)
        archive = directory / "source.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("Mod/mod_info.json", json.dumps({"version": "2.0.0"}))
            output.writestr(
                "Mod/data/world/factions/player.faction",
                json.dumps({"portraits": {
                    "standard_male": paths[:1], "standard_female": paths[1:]
                }}),
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
            self.assertEqual(len(list(dist.glob("*.zip"))), 5)
            for color in ("Red", "Purple", "Orange", "Blue", "General"):
                with zipfile.ZipFile(dist / f"Starlit-Faces-{color}-2.0.0.zip") as archive:
                    folder = f"StarlitFaces{color}"
                    faction = json.loads(archive.read(
                        f"{folder}/data/world/factions/player.faction"
                    ))
                    gender = "standard_male" if color == "General" else "standard_female"
                    self.assertEqual(list(faction["portraits"]), [gender])
                    paths = faction["portraits"][gender]
                    self.assertEqual(len(paths), 1)
                    self.assertEqual(archive.read(folder + "/" + paths[0]), b"portrait bytes")

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


if __name__ == "__main__":
    unittest.main()
