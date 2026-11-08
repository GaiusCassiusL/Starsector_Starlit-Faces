# Starlit Faces

Starlit Faces is a Starsector portrait pack for **0.98a-RC8**. It adds 86 portraits to the player portrait pool: 8 male portraits and 78 female portraits.

## Install

1. Choose a ZIP from `dist`.
2. Extract it into Starsector's `mods` folder. Each ZIP contains its own mod folder, such as `StarlitFaces` or `StarlitFacesRed`.
3. Enable the extracted mod in Starsector's launcher.

Install either the all-portraits ZIP or the five category ZIPs. Do not install both sets together, or portraits may appear more than once.

## Rebuild the category ZIPs

`Starlit-Faces-All-1.0.0.zip` is the canonical source mod. The other five ZIPs are generated from its images, metadata, and player portrait registrations; do not edit the generated ZIPs by hand.

With Python 3 installed, run this from the repository root:

```sh
python scripts/build_distributions.py
```

The script replaces the Red, Purple, Orange, Blue, and General ZIPs in `dist`. It validates the canonical ZIP and checks that every portrait is registered and assigned to exactly one category.

The script automatically selects the sole `Starlit-Faces-All-*.zip` in `dist` and uses its metadata version for output filenames. If multiple versions exist, select one explicitly:

```sh
python scripts/build_distributions.py --canonical dist/Starlit-Faces-All-1.0.0.zip
```

All categories are validated and staged before existing builds are replaced. Publication errors restore the previous builds.

Run the regression tests with `python -m unittest discover -s tests`.

## Available builds

| ZIP | Contents |
| --- | --- |
| `Starlit-Faces-All-1.0.0.zip` | All 86 portraits: 8 male and 78 female |
| `Starlit-Faces-Red-1.0.0.zip` | 21 portraits with `red` in the filename: 2 male and 19 female |
| `Starlit-Faces-Purple-1.0.0.zip` | 21 portraits with `purple` in the filename: 2 male and 19 female |
| `Starlit-Faces-Orange-1.0.0.zip` | 21 portraits with `orange` in the filename: 2 male and 19 female |
| `Starlit-Faces-Blue-1.0.0.zip` | 10 portraits with `blue` in the filename: all female |
| `Starlit-Faces-General-1.0.0.zip` | The remaining 13 portraits without those color names: 2 male and 11 female |

The five category builds split all 86 portraits into non-overlapping groups. Marine1, Marine2, and their color variants are registered as male portraits; the others are registered as female portraits.

When upgrading from an older portrait set, remove the previous Starlit Faces mod folders before extracting these builds. Do not merge folders: obsolete image files may otherwise remain on disk.

## Project layout

- `dist/Starlit-Faces-All-1.0.0.zip` — authoritative mod source; edit this archive to update portraits or metadata.
- `mod_info.json`, `data/`, and `graphics/` — noncanonical extracted copy for inspection or local installation. Changes here do not affect builds; keep these files synchronized manually when editing the canonical ZIP.
- `dist/` — canonical All ZIP and generated category ZIPs.
- `scripts/` — distribution build script.
- `tests/` — build regression tests.
