#!/usr/bin/env python3
"""Build the five category portrait mods from the canonical all-portraits ZIP."""

import argparse
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
GROUPS = (
    ("red", "Red", "StarlitFacesRed"),
    ("purple", "Purple", "StarlitFacesPurple"),
    ("orange", "Orange", "StarlitFacesOrange"),
    ("blue", "Blue", "StarlitFacesBlue"),
    (None, "General", "StarlitFacesGeneral"),
)
PORTRAIT_PREFIX = "graphics/portraits/"


def safe_archive_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe path in canonical archive: {name}")
    return path


def build(canonical, dist):
    if not canonical.is_file():
        raise FileNotFoundError(f"Canonical source ZIP not found: {canonical}")

    with zipfile.ZipFile(canonical) as source:
        files = {}
        for info in source.infolist():
            path = safe_archive_path(info.filename)
            if info.is_dir():
                continue
            if info.filename in files:
                raise ValueError(f"Duplicate path in canonical archive: {info.filename}")
            files[info.filename] = source.read(info)

    roots = {PurePosixPath(name).parts[0] for name in files}
    if len(roots) != 1:
        raise ValueError("Canonical ZIP must contain exactly one top-level mod folder.")
    source_root = roots.pop()
    mod_info_path = f"{source_root}/mod_info.json"
    faction_path = f"{source_root}/data/world/factions/player.faction"
    if mod_info_path not in files or faction_path not in files:
        raise ValueError("Canonical ZIP must contain mod_info.json and player.faction.")

    metadata = json.loads(files[mod_info_path])
    version = metadata.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", version):
        raise ValueError("Canonical version must be a filename-safe version string.")
    faction = json.loads(files[faction_path])
    portraits = faction.get("portraits", {})
    male = portraits.get("standard_male", [])
    female = portraits.get("standard_female", [])
    if not isinstance(male, list) or not isinstance(female, list):
        raise ValueError("Canonical portrait pools must be arrays.")
    all_paths = male + female
    if not all_paths or any(
        not isinstance(path, str)
        or not path.startswith(PORTRAIT_PREFIX)
        or ".." in PurePosixPath(path).parts
        for path in all_paths
    ):
        raise ValueError("Canonical portrait registrations contain invalid paths.")
    if len(all_paths) != len(set(all_paths)):
        raise ValueError("Canonical portrait registrations contain duplicate paths.")

    portrait_files = {
        name[len(source_root) + 1 :]: content
        for name, content in files.items()
        if name.startswith(f"{source_root}/{PORTRAIT_PREFIX}")
    }
    if set(all_paths) != set(portrait_files):
        missing = sorted(set(all_paths) - set(portrait_files))
        unregistered = sorted(set(portrait_files) - set(all_paths))
        raise ValueError(
            f"Canonical registrations/assets differ; missing={missing}, "
            f"unregistered={unregistered}"
        )

    outputs = []
    seen = set()
    for color, label, folder in GROUPS:
        if color is None:
            selected = {
                path
                for path in all_paths
                if not re.search(r"red|purple|orange|blue", PurePosixPath(path).name, re.I)
            }
        else:
            selected = {
                path
                for path in all_paths
                if color in PurePosixPath(path).name.casefold()
            }
        if not selected:
            raise ValueError(f"No portraits matched the {label} group.")
        if seen & selected:
            raise ValueError(f"Portraits appear in multiple groups: {sorted(seen & selected)}")
        seen.update(selected)

        group_faction = {"portraits": {}}
        for key, registered in (
            ("standard_male", male),
            ("standard_female", female),
        ):
            filtered = [path for path in registered if path in selected]
            if filtered:
                group_faction["portraits"][key] = filtered

        group_metadata = dict(metadata)
        group_metadata.update(
            {
                "id": f"starlit_faces_{label.casefold()}",
                "name": f"Starlit Faces - {label}",
                "description": (
                    f"Adds {len(selected)} portraits in the {label.casefold()} "
                    "group to the player's portrait pool."
                ),
            }
        )
        output_name = f"Starlit-Faces-{label}-{version}.zip"
        outputs.append((output_name, folder, selected, group_metadata, group_faction))

    if seen != set(all_paths):
        raise ValueError(f"Some portraits were not assigned to a group: {sorted(set(all_paths) - seen)}")

    dist.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".starlit-build-", dir=dist) as temporary:
        stage = Path(temporary)
        for name, folder, selected, group_metadata, group_faction in outputs:
            with zipfile.ZipFile(
                stage / name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as output:
                output.writestr(
                    f"{folder}/mod_info.json", json.dumps(group_metadata, indent=2) + "\n"
                )
                output.writestr(
                    f"{folder}/data/world/factions/player.faction",
                    json.dumps(group_faction, indent=2) + "\n",
                )
                for path in sorted(selected, key=str.casefold):
                    output.writestr(f"{folder}/{path}", portrait_files[path])
            with zipfile.ZipFile(stage / name) as check:
                if check.testzip() is not None:
                    raise ValueError(f"Generated ZIP failed integrity check: {name}")

        backups = stage / "backups"
        backups.mkdir()
        published = []
        try:
            for name, *_ in outputs:
                target = dist / name
                if target.exists():
                    shutil.copy2(target, backups / name)
                (stage / name).replace(target)
                published.append(name)
        except OSError:
            for name in reversed(published):
                if (backups / name).exists():
                    (backups / name).replace(dist / name)
                else:
                    (dist / name).unlink()
            raise

    for name, _, selected, _, _ in outputs:
        print(f"Built {name} ({len(selected)} portraits)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, help="Path to the canonical All ZIP.")
    args = parser.parse_args()
    canonical = args.canonical
    if canonical is None:
        candidates = sorted(DIST.glob("Starlit-Faces-All-*.zip"))
        if len(candidates) != 1:
            parser.error("Expected one All ZIP in dist; select one with --canonical.")
        canonical = candidates[0]
    build(canonical, DIST)


if __name__ == "__main__":
    main()
