#!/usr/bin/env python3
"""Build portrait packs and Version Checker metadata from the canonical All ZIP."""

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
RAW_URL = "https://raw.githubusercontent.com/GaiusCassiusL/Starsector_Starlit-Faces/main"


def version_metadata(metadata, label):
    version = metadata["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version Checker requires a major.minor.patch numeric version.")
    major, minor, patch = map(int, version.split("."))
    return {
        "masterVersionFile": f"{RAW_URL}/dist/{metadata['id']}.version",
        "modName": metadata["name"],
        "modVersion": {"major": major, "minor": minor, "patch": patch},
        "directDownloadURL": f"{RAW_URL}/dist/Starlit-Faces-{label}-{version}.zip",
    }


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
    if canonical.name != f"Starlit-Faces-All-{version}.zip":
        raise ValueError("Canonical ZIP filename must match its mod metadata version.")
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

    outputs.append((canonical.name, source_root, set(all_paths), metadata, faction))
    version_files = {}
    for _, _, _, mod_metadata, _ in outputs:
        label = "All" if mod_metadata["id"] == metadata["id"] else mod_metadata["name"].split(" - ")[-1]
        filename = f"{mod_metadata['id']}.version"
        safe_archive_path(filename)
        if "/" in filename:
            raise ValueError("Mod ID must not contain path separators.")
        version_files[filename] = json.dumps(
            version_metadata(mod_metadata, label), indent=2
        ) + "\n"

    dist.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".starlit-build-", dir=dist) as temporary:
        stage = Path(temporary)
        for name, folder, selected, group_metadata, group_faction in outputs:
            with zipfile.ZipFile(
                stage / name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as output:
                if folder == source_root:
                    for source_path, content in files.items():
                        relative = source_path[len(source_root) + 1:]
                        if relative not in (
                            "mod_info.json", "data/world/factions/player.faction",
                            "data/config/version/version_files.csv",
                            f"{metadata['id']}.version",
                        ) and not relative.startswith(PORTRAIT_PREFIX):
                            output.writestr(source_path, content)
                output.writestr(
                    f"{folder}/mod_info.json", json.dumps(group_metadata, indent=2) + "\n"
                )
                output.writestr(
                    f"{folder}/data/world/factions/player.faction",
                    json.dumps(group_faction, indent=2) + "\n",
                )
                version_name = f"{group_metadata['id']}.version"
                output.writestr(f"{folder}/{version_name}", version_files[version_name])
                output.writestr(
                    f"{folder}/data/config/version/version_files.csv",
                    f"version file\n{version_name}\n",
                )
                for notice in (() if folder == source_root else ("LICENSE", "PORTRAIT_NOTICE.txt")):
                    source_path = f"{source_root}/{notice}"
                    if source_path in files:
                        output.writestr(f"{folder}/{notice}", files[source_path])
                for path in sorted(selected, key=str.casefold):
                    output.writestr(f"{folder}/{path}", portrait_files[path])
            with zipfile.ZipFile(stage / name) as check:
                if check.testzip() is not None:
                    raise ValueError(f"Generated ZIP failed integrity check: {name}")

        for name, content in version_files.items():
            (stage / name).write_text(content, encoding="utf-8")
        publication_names = [item[0] for item in outputs] + list(version_files)
        backups = Path(tempfile.mkdtemp(prefix=".starlit-backups-", dir=dist))
        published = []
        preserve_backups = False
        try:
            for name in publication_names:
                target = dist / name
                if target.exists():
                    shutil.copy2(target, backups / name)
                (stage / name).replace(target)
                published.append(name)
        except OSError:
            try:
                for name in reversed(published):
                    if (backups / name).exists():
                        (backups / name).replace(dist / name)
                    else:
                        (dist / name).unlink()
            except OSError as rollback_error:
                preserve_backups = True
                raise RuntimeError(
                    f"Build publication and rollback failed. Recovery backups: {backups}"
                ) from rollback_error
            raise
        finally:
            if not preserve_backups:
                shutil.rmtree(backups)

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
    canonical = canonical.resolve()
    if canonical.parent != DIST.resolve():
        parser.error("The canonical ZIP must be in dist so its update download URL is valid.")
    build(canonical, DIST)


if __name__ == "__main__":
    main()
