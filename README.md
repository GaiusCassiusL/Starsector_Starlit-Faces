# Starlit Faces

Starlit Faces is a Starsector portrait pack for **0.98a-RC8**. It adds 82 portraits to the player portrait pool: 8 male portraits and 74 female portraits.

<p align="center">
  <img src="graphics/portraits/Emma1.png" alt="Emma" width="128">
  <img src="graphics/portraits/Inde1-red.png" alt="Inde — red variant" width="128">
  <img src="graphics/portraits/Sophia1-orange.png" alt="Sophia — orange variant" width="128">
  <img src="graphics/portraits/Sophia2.png" alt="Sophia" width="128">
  <img src="graphics/portraits/Mia2-purple.png" alt="Mia — purple variant" width="128">
  <img src="graphics/portraits/Olivia1-orange.png" alt="Olivia — orange variant" width="128">
</p>

## License and portrait notice

The entire project, including portraits, scripts, configuration, and documentation, is dedicated under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). You may use, modify, redistribute, and incorporate it into your own works, including commercially, without attribution. See `LICENSE`.

The portraits are AI-generated depictions intended to represent fictional characters. No endorsement by or affiliation with any real person is intended. This does not guarantee that no portrait resembles a real person. CC0 covers only rights held by the contributor and does not grant third-party likeness, privacy, publicity, or trademark rights. See `PORTRAIT_NOTICE.txt`.

## Install

1. Choose a ZIP from `dist`.
2. Extract it into Starsector's `mods` folder. Each ZIP contains its own mod folder, such as `StarlitFaces` or `StarlitFacesRed`.
3. Enable the extracted mod in Starsector's launcher.

Install either the all-portraits ZIP or any selection of the five category ZIPs. You do not need all five category packs. Do not combine All with category packs, or portraits may appear more than once.

Python is needed only to rebuild the distributions, not to install or play the mod.

## Rebuild the category ZIPs

`Starlit-Faces-All-1.0.1.zip` is the canonical source mod. The other five ZIPs are generated from its images, metadata, and player portrait registrations; do not edit the generated ZIPs by hand.

With Python 3 installed, run this from the repository root:

```sh
python scripts/build_distributions.py
```

The script replaces the Red, Purple, Orange, Blue, and General ZIPs in `dist`, refreshes Version Checker metadata inside the canonical All ZIP, and generates six public `.version` files. It validates the canonical ZIP and checks that every portrait is registered and assigned to exactly one category.

The script automatically selects the sole `Starlit-Faces-All-*.zip` in `dist` and uses its metadata version for output filenames. If multiple versions exist, select one explicitly:

```sh
python scripts/build_distributions.py --canonical dist/Starlit-Faces-All-1.0.1.zip
```

All categories are validated and staged before existing builds are replaced. Publication errors restore the previous builds. If restoration also fails, the script reports a recovery backup directory and preserves it for manual recovery.

Run the regression tests with `python -m unittest discover -s tests`.

## TriOS and Version Checker

All six packs include TriOS-compatible Version Checker metadata: their own `.version` file and `data/config/version/version_files.csv`. The metadata provides update checks and matching pack download URLs without requiring a new mod dependency. The integration has not yet been tested in TriOS or in-game.

Public master files live in `dist` on the repository's `main` branch. Download links point directly to the corresponding ZIP in that branch; they become available only after the generated files are published there. They do not depend on a GitHub Release existing.

For an update, change the version in the canonical ZIP's `mod_info.json`, rename the ZIP to `Starlit-Faces-All-<version>.zip`, and run the build script. Use a numeric `major.minor.patch` version. Publish all six ZIPs and all six `.version` files together; do not publish a master version before its matching download is available.

Before rebuilding, update this README's version numbers and pack counts, then replace `StarlitFaces/README.md` inside the canonical ZIP with the updated README. Editing the repository README alone does not update the bundled copy. Keep the noncanonical root `mod_info.json` and `starlit_faces.version` synchronized with the canonical metadata and generated `dist/starlit_faces.version` after a version bump.

## Available builds

| ZIP | Contents |
| --- | --- |
| [Starlit-Faces-All-1.0.1.zip](dist/Starlit-Faces-All-1.0.1.zip) | All 82 portraits: 8 male and 74 female |
| [Starlit-Faces-Red-1.0.1.zip](dist/Starlit-Faces-Red-1.0.1.zip) | 20 portraits with `red` in the filename: 2 male and 18 female |
| [Starlit-Faces-Purple-1.0.1.zip](dist/Starlit-Faces-Purple-1.0.1.zip) | 20 portraits with `purple` in the filename: 2 male and 18 female |
| [Starlit-Faces-Orange-1.0.1.zip](dist/Starlit-Faces-Orange-1.0.1.zip) | 20 portraits with `orange` in the filename: 2 male and 18 female |
| [Starlit-Faces-Blue-1.0.1.zip](dist/Starlit-Faces-Blue-1.0.1.zip) | 10 portraits with `blue` in the filename: all female |
| [Starlit-Faces-General-1.0.1.zip](dist/Starlit-Faces-General-1.0.1.zip) | The remaining 12 portraits without those color names: 2 male and 10 female |

The five category builds split all 82 portraits into non-overlapping groups. Marine1, Marine2, and their color variants are registered as male portraits; the others are registered as female portraits.

When upgrading from an older portrait set, remove the previous Starlit Faces mod folders before extracting these builds. Do not merge folders: obsolete image files may otherwise remain on disk.

## Project layout

- `dist/Starlit-Faces-All-1.0.1.zip` — authoritative mod source; edit this archive to update portraits or metadata.
- `mod_info.json`, `data/`, and `graphics/` — noncanonical extracted copy for inspection or local installation. Changes here do not affect builds; keep these files synchronized manually when editing the canonical ZIP.
- `dist/` — canonical All ZIP, generated category ZIPs, and six generated master `.version` files for online update checks.
- `scripts/` — distribution build script.
- `tests/` — build regression tests.
