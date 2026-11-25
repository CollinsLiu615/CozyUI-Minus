# CozyUI+ low-version backport — technical notes

This document records how the backport was derived and what was measured. Every claim below comes
from comparing the official client jars or the upstream pack; nothing here relies on in-game
impressions.

---

## 1. It is a resource pack, not a mod

The upstream repository contains a README, promotional material, `.psd` sources and an `icon.zip` —
no Java source, no `build.gradle`, no `fabric.mod.json`. Its Modrinth project type is `resourcepack`.

Consequences:

- No JDK, Gradle, Loom or mappings are involved. A backport is a problem of **file paths and GUI
  geometry**.
- The unit of work is a texture sheet, not a class. Compatibility is decided by whether a texture
  exists at a given path in a given version and whether its internal layout matches.
- Nothing can be "compiled out"; every incompatibility has to be resolved by pruning, remapping or
  falling back to vanilla.

## 2. Pack formats

`pack.mcmeta` declares `pack_format` as one integer. The client compares it against the value it
expects and shows the yellow "made for an older/newer version" notice on mismatch. The expected
values were read from `version.json` inside each client jar:

| Version | `pack_version.resource` |
|---|:--:|
| 1.14.4 | 4 |
| 1.16.1 | 5 |
| 1.16.5 | 6 |
| 1.17.1 | 7 |
| 1.18.2 | 8 |
| 1.19 / 1.19.2 | 9 |
| 1.19.3 | 12 |
| 1.19.4 | 13 |
| 1.20.1 | 15 |
| 1.20.2 | 18 |

The 1.8.9, 1.10.2 and 1.12.2 jars have no `version.json`; their values (1, 2, 3) come from the
release notes. The 1.21.x jars are launcher stubs and contain no pack metadata at all.

The resulting ranges are:

```
< 1.9 -> 1      < 1.11 -> 2      < 1.13 -> 3      < 1.15 -> 4
< 1.16.2 -> 5   < 1.17 -> 6      < 1.18 -> 7      < 1.19 -> 8
< 1.19.3 -> 9   < 1.19.4 -> 12   otherwise -> 13
```

Because a file can declare only one value, a pack covering several formats will always show the
notice on part of its range. The only way to have no notice anywhere is one file per format — see §7.

## 3. Measured differences between adjacent versions

For every adjacent pair of baseline versions, the largest per-sheet difference was computed on the
alpha masks, excluding full-screen textures (`panorama_*`, `demo_background`) which are photographic
and differ every release:

| Boundary | Largest difference | Sheet | Effect of merging |
|---|--:|---|---|
| 1.8.9 → 1.10.2 | 5.2 % | `inventory` | safe |
| 1.10.2 → 1.12.2 | 2.4 % | `inventory` | safe |
| 1.12.2 → 1.14.4 | 10.3 % | `recipe_book` | break |
| 1.14.4 → 1.16.1 | 100 % | `checkbox` | break |
| 1.16.1 → 1.16.5 | 0.9 % | — | safe |
| 1.16.5 → 1.17.1 | 4.3 % | `recipe_button` | safe |
| 1.17.1 → 1.18.2 | 3.1 % | — | safe |
| 1.18.2 → 1.19.2 | 0.0 % | — | safe |
| 1.19.2 → 1.19.3 | 55.9 % | `chat_tags` | break |
| 1.19.3 → 1.19.4 | 0.0 % | — | safe |
| 1.19.4 → 1.20.1 | 0.0 % | — | safe |

The `1.14.4 → 1.16.1` row is not a gradual drift: `checkbox.png` changes shape entirely and
`widgets.png` by 63.5 %. That is a redesign, not a rescale.

Whether a difference can be bridged depends on its **direction**. Comparing 1.8.9 against 1.12.2
gives 7.0 % for `inventory`, of which 2609 px are *added* regions — older versions simply never read
them, so merging would be harmless. Comparing 1.8.9 against 1.14.4 gives 12.9 %, of which 3001 px
are *deleted* regions: the 1.14.4 sheet has been rearranged, so a 1.8 client would draw missing
blocks. Additive differences can be merged; subtractive ones cannot.

Container panels hold up well across the whole range. IoU of the alpha mask against 1.20.1:

| Sheet | IoU |
|---|--:|
| `container/generic_54` | 0.988 |
| `container/brewing_stand` | 0.986 |
| `container/horse` | 0.980 |
| `container/enchanting_table` | 0.945 |
| `container/inventory` | 0.869 |
| `gui/icons` | 0.560 |
| `gui/widgets` | 0.341 |

`widgets.png` and `icons.png` are the two sheets that get rearranged, which is why controls fall
back to vanilla below 1.13.

## 4. The creative-inventory tabs

`gui/container/creative_inventory/tabs.png` changed geometry twice and is the single most
error-prone sheet.

Column runs measured on the alpha mask:

| Versions | Runs |
|---|---|
| 1.8.9, 1.10.2, 1.12.2, 1.14.4, 1.16.5, 1.19.2 | `[(0,196), (232,24)]` |
| 1.20.1 | `[(0,208), (232,24)]` |

The upstream pack draws 7 columns at 26 px (182 px). 1.19.2 expects 7 × 28 = 196 px, so the columns
are stretched horizontally. 1.19.3, 1.19.4 and 1.20.1 expect 8 × 26 = 208 px, which is the same
column width with one more tab — stretching there would be wrong, so the builder checks the target
content width and leaves the sheet untouched when it is already 196 or 208 px.

The tab artwork itself lives in separate `tab_*_tab.png` files, so a stride mismatch can never put
the wrong icon on a tab; only the plate seams would show it.

## 5. How the builder works

`tools/build.py` builds one artifact per band defined in `tools/packformats.json`:

1. **Prune.** Keep only paths that exist in the target client jar. Font JSON, OptiGUI metadata,
   sounds, sprite-era paths and mod textures are dropped for versions that cannot read them.
2. **Remap geometry.** For sheets whose layout changed, rescale or re-stack the regions while
   keeping the source artwork. Each rule declares source width, target width, column count, the
   column mapping and any preserved tail region.
3. **Gate.** Compute the agreement ratio `IoU(pack, target) / IoU(pack, 1.20.1)` for every candidate
   sheet. If the ratio falls below the band threshold, the sheet is dropped and the version keeps
   its vanilla texture. Non-integer scale factors are dropped unconditionally as `bad_scale`.
4. **Write.** Emit `pack.mcmeta` with the exact `pack_format`, the icon, and a report entry per
   texture.

Using a ratio rather than a raw IoU matters: it asks "is this sheet as compatible with the target as
it is with the baseline?", which is the actual question, and it stays meaningful for sheets that are
partially transparent.

## 6. Self-check without the game

`tools/validate.py` performs 11 checks per artifact, none of which need Minecraft:

- `pack_format` equals the expected value for the band;
- `pack.png` present and 96×96 or smaller;
- every JSON parses (only the first object in multi-object `.mcmeta` files is read, which is how the
  upstream `button_highlighted` file is structured);
- every `.png.mcmeta` has a matching `.png`, and every animated sheet's height is a multiple of its
  declared frame height;
- every texture path exists in the target client jar (an override that can never load is a bug);
- every model and blockstate reference resolves;
- font glyph sheets referenced by a font JSON exist;
- no `.DS_Store`, no duplicate zip entries, no zero-byte files.

Result for the current set: 11/11.

## 7. Band selection: why eleven files

Given the measurements in §3 and the format table in §2, the bands follow the format boundaries
exactly. Merging two formats into one file is possible — the pack would still load — but the file
would have to declare one number and would therefore show the notice on the other format's range.

For this release the decision was **zero warnings**, so bands are cut at format boundaries:

```
1.6.1-1.8.9   1.9-1.10.2   1.11-1.12.2   1.13-1.14.4   1.15-1.16.1   1.16.2-1.16.5
1.17-1.17.1   1.18-1.18.2   1.19-1.19.2   1.19.3   1.19.4
```

The cost is 11 files instead of 4. The benefit is that no version in 1.6.1 – 1.19.4 ever sees a
format notice, and every file serves a single generation, so layout accuracy is at its best.

## 8. Pushing down to 1.6.1

Pack format 1 officially spans 1.6.1 – 1.8.9, so the oldest band was extended to the whole range.
Verified against the 1.6.1 and 1.6.4 client jars:

- 1.6.1 and 1.6.4 were downloaded and compared against 1.8.9 sheet by sheet;
- of the 26 GUI sheets the artifact ships, exactly **one** differs: `container/enchanting_table.png`,
  by 1.5 % of its pixels;
- `widgets.png` and `icons.png` are pixel-identical, so the gradient rectangles
  (`(0,69,182,5)` and `(0,0,24,24)`) apply unchanged.

1.6.1 is also where Minecraft introduced the current `assets/` resource-pack layout. 1.5.2 and older
use the old texture-pack structure and cannot carry this pack at all, which is why 1.6.1 is the
lower bound rather than an arbitrary choice.

## 9. RGB gradient

The upstream cycle is not a shader and does not need OptiFine. It uses the sprite-animation format
added in 1.20.2:

| Sprite | Size | Frames | Frame height | `frametime` | Cycle |
|---|--:|--:|--:|--:|--:|
| `hud/experience_bar_progress` | 728×160 | 8 | 20 | 100 | 40 s |
| `hud/hotbar_selection` | 96×736 | 8 | 92 | 100 | 40 s |
| `hud/jump_bar_progress` | 728×160 | 8 | 20 | 100 | 40 s |

All three set `interpolate: true`, so frames blend rather than jump. The hue sequence, taken as the
median of coloured pixels per frame, is:

```
11, 26, 50, 93, 124, 146, 174, 205   (0-255)
orange, yellow, yellow-green, green, cyan, blue, purple, magenta
```

That sprite system does not exist below 1.20.2, and `.mcmeta` `animation` applies to a **whole
texture**, so a single rectangle cannot be animated on its own. The port therefore turns the entire
sheet into an 8-frame animation in which only the target rectangle changes colour and every other
pixel is byte-identical between frames.

Measured target rectangles, identical across 1.6.1 – 1.19.4:

| Element | Sheet | Rectangle (1×) | Evidence |
|---|---|---|---|
| Experience bar foreground | `icons.png` | `(0,69,182,5)` | 906 px, saturation 0.59, mean `#436830` |
| Hotbar highlight | `widgets.png` | `(0,0,24,24)` | 576 px, mean `#3D3D30` |
| Boss bar (untouched) | `bars.png` | `y81..118`, 8 pairs | pure black, tinted by code |

`bars.png` holds only boss bars, which are black and coloured by the game, so they must not be
animated. The experience bar has been in `icons.png` since 1.8.

Two recolouring modes are used:

- **hue** for the experience bar: the artwork is already saturated, so replacing the hue channel
  keeps shading, outline and rounded corners intact;
- **tint** for the hotbar highlight: the artwork is grey (saturation 0), where changing hue alone
  would be invisible, so saturation is raised as well.

### Frame-rate conflict

`widget/button_highlighted` is a 16-frame pulse at `frametime: 1`. It shares `widgets.png` with the
hotbar highlight, and one sheet can carry only one animation definition. Matching the pulse would
require 8 × 100 = 800 frames for the highlight. The pulse was therefore dropped; upstream itself
marks that effect as requiring 1.21+.

### Cost

| Sheet | Frame size | Frames | VRAM |
|---|--:|--:|--:|
| `icons.png` | 1024×1024 | 8 | 32 MB |
| `widgets.png` | 1024×1024 | 8 | 32 MB |

Deleting the corresponding `.png.mcmeta` disables the animation and the texture reverts to a single
frame with no misalignment.

## 10. Not verified

There is no in-game verification in this repository. Everything above is static evidence: pixel
comparison against official jars, structural validation and reference resolution. Before a release,
a smoke test is recommended on two versions — 1.19.4 (zero remapping, should be identical to
upstream) and 1.6.1 (largest distance from the baseline) — checking the creative-inventory tab icons
first, since that sheet is the most fragile.

## Appendix: fetching inputs

```bash
python3 tools/fetch_inputs.py
```

This downloads the upstream v1.10 pack from the Modrinth CDN and the twelve client jars named in
`tools/packformats.json` from Mojang's `version_manifest_v2`. None of them are tracked in git.
