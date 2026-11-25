# CozyUI-

An unofficial backport of [CozyUI+](https://modrinth.com/resourcepack/cozyui-plus) to Minecraft
**1.6.1 – 1.19.4**, shipped as 11 files — one per resource-pack format generation — covering
**63 release versions with zero format warnings**.

**Download:** [Modrinth](https://modrinth.com/resourcepack/cozyui-minus) · [CurseForge](https://www.curseforge.com/minecraft/texture-packs/cozyui-minus)

> **CozyUI+ is a resource pack, not a mod.** The upstream repository contains only a README,
> artwork and PSD sources: no Java code, no `build.gradle`. Backporting it is therefore a question
> of texture paths and GUI geometry rather than loaders, mappings or mixins, and it needs no JDK.
>
> Technical notes and measurements: [`docs/porting-notes.md`](docs/porting-notes.md) ·
> [中文](docs/porting-notes.zh-CN.md) ·
> Store copy: [`docs/description-en.md`](docs/description-en.md)

---

## Download and install

| Platform | Link |
|---|---|
| **Modrinth** | <https://modrinth.com/resourcepack/cozyui-minus> |
| **CurseForge** | <https://www.curseforge.com/minecraft/texture-packs/cozyui-minus> |

Pick the file for your game version, drop it into `.minecraft/resourcepacks/` and enable it in
*Options → Resource Packs*. Do **not** unpack it. Every file uses the same icon `assets/pack.png`.

Packaged builds are not hosted in this repository. `dist/` is produced locally, as described under
[Building from source](#building-from-source).

### Why 11 files instead of one

`pack_format` is a single integer, and the game compares it against the value it expects for the
running version. Any mismatch produces the yellow "made for an older/newer version" notice. A pack
that declares one number for a whole range will therefore always show that notice on part of the
range; avoiding it everywhere requires **one file per pack format**.

| File | Minecraft | `pack_format` | Size | RGB gradient |
|---|---|:--:|--:|---|
| `CozyUI-_1.6.1-1.8.9.zip` | 1.6.1 – 1.8.9 | 1 | 5.3 MB | experience bar |
| `CozyUI-_1.9-1.10.2.zip` | 1.9 – 1.10.2 | 2 | 5.4 MB | experience bar |
| `CozyUI-_1.11-1.12.2.zip` | 1.11 – 1.12.2 | 3 | 6.0 MB | experience bar |
| `CozyUI-_1.13-1.14.4.zip` | 1.13 – 1.14.4 | 4 | 39.2 MB | bar + hotbar highlight |
| `CozyUI-_1.15-1.16.1.zip` | 1.15 – 1.16.1 | 5 | 39.3 MB | bar + hotbar highlight |
| `CozyUI-_1.16.2-1.16.5.zip` | 1.16.2 – 1.16.5 | 6 | 39.3 MB | bar + hotbar highlight |
| `CozyUI-_1.17-1.17.1.zip` | 1.17 – 1.17.1 | 7 | 39.3 MB | bar + hotbar highlight |
| `CozyUI-_1.18-1.18.2.zip` | 1.18 – 1.18.2 | 8 | 39.3 MB | bar + hotbar highlight |
| `CozyUI-_1.19-1.19.2.zip` | 1.19 – 1.19.2 | 9 | 39.3 MB | bar + hotbar highlight |
| `CozyUI-_1.19.3.zip` | 1.19.3 | 12 | 39.3 MB | bar + hotbar highlight |
| `CozyUI-_1.19.4.zip` | 1.19.4 | 13 | 39.3 MB | bar + hotbar highlight |

Coverage: 36 release versions in 1.6.1 – 1.12.2, 8 in 1.13 – 1.14.4, 17 in 1.15 – 1.19.2 and
2 in 1.19.3 – 1.19.4 — **63 in total, none missing**. Minecraft 1.20 and newer are served by the
upstream pack, whose official support starts there, so the ranges do not overlap.

### RGB gradient

The upstream hue cycle uses the sprite-animation format introduced in 1.20.2: 8 frames at
`frametime: 100` (5 s per frame) with `interpolate: true`, i.e. a **40-second cycle**. That format
does not exist below 1.20.2, so `tools/animate.py` re-implements it by turning the whole sheet into
an 8-frame animation in which only the relevant rectangle changes colour:

- experience bar foreground — `icons.png`, `(0,69,182,5)`;
- hotbar highlight — `widgets.png`, `(0,0,24,24)`.

Both rectangles are identical across 1.6.1 – 1.19.4, measured against the official client jars.
Hue values are the median of the upstream frames: orange → yellow → yellow-green → green → cyan →
blue → purple → magenta ([preview](docs/img/gradient_preview.png)).

Cost: `animation` applies to a whole texture, so those two sheets become 1024×8192 and occupy about
32 MB of VRAM each, 64 MB combined. Removing the corresponding `.png.mcmeta` disables the animation
without any misalignment. The 1.6.1 – 1.12.2 files ship the vanilla `widgets.png`, so those versions
get the experience bar cycle but not the highlight.

### Version coverage

| | 1.13+ | 1.6.1 – 1.12.2 |
|---|:--:|:--:|
| Container panels (inventory, chest, furnace, crafting, brewing, beacon, hopper, anvil, enchanting, villager…) | ✅ | ✅ |
| Title-screen panorama | ✅ | ✅ |
| Buttons, sliders, text fields, hotbar (`widgets.png`) | ✅ | ❌ vanilla |
| HUD hearts / food / armour (`icons.png`) | ✅ | ✅ |
| Creative tab plates | ✅ | ✅ |
| Bundled font (Emoji+ / MCsans+) | ✅ | ❌ not applicable |
| Brewing recipes & enchantment icons | ✅ | ❌ depend on the bundled font |
| Mod skins | ✅ | ❌ |
| Colored containers via OptiGUI | ✅ with the mod | ❌ |
| RGB experience bar | ✅ | ✅ |
| RGB hotbar highlight | ✅ | ❌ |

Where a sheet's layout changed too much between versions, the port leaves it vanilla rather than
shipping a misaligned texture.

## Building from source

The repository contains no binaries: the packaged zips are published on Modrinth and CurseForge, the
Mojang client jars are copyrighted, and the upstream pack is 39 MB — none of them belong in git.
Fetch the inputs first (about 250 MB):

```bash
python3 tools/fetch_inputs.py    # upstream v1.10 pack + 12 vanilla client jars
python3 tools/build.py           # 11 packs -> dist/
python3 tools/animate.py         # inject the RGB gradient
python3 tools/validate.py        # self-check, expects 11/11
```

Requirements: Python 3.9+, `pillow`, `numpy` (`scipy` only for `coverage_matrix.py`).

## Repository layout

```
tools/build.py               backport builder (version bands -> pack.mcmeta, pruning, layout remap, agreement gate)
tools/animate.py             RGB gradient injector (upstream 8-frame hues -> legacy sheet animation)
tools/validate.py            artifact self-check, no game required
tools/coverage_matrix.py     layout agreement matrix (artifact x version)
tools/make_proof.py          three-column comparison images (upstream / backport / vanilla)
tools/fetch_inputs.py        fetch build inputs (not tracked)
tools/packformats.json       pack format table with the per-band policy
docs/porting-notes.md        full technical notes and measurements
docs/porting-notes.zh-CN.md  the same, in Chinese
docs/description-en.md       store copy for Modrinth / CurseForge
docs/img/                    comparison images and the gradient preview
assets/pack.png              project icon, copied into every artifact (build input; not upstream's)
work/build-report.json       build report: per-texture agreement ratios and drop reasons
```

## Known limitations

1. **Not verified in-game.** All conclusions come from per-image comparison against the official
   client jars, structural self-checks and resource-reference validation (`tools/validate.py`
   reports 11/11). No in-game screenshots were taken.
2. **1.6.1 – 1.12.2 keep vanilla buttons and controls.** The `widgets.png` layout of that era
   differs from 1.13+ by roughly 37 %, so the whole sheet is left vanilla. `icons.png` is kept, so
   the HUD and the experience bar cycle remain themed.
3. **The RGB gradient has a VRAM cost.** Both animated sheets become 1024×8192 at 4×, about 64 MB
   combined. Removing the `.png.mcmeta` files reverts them to a single frame with no misalignment.
   The button-highlight pulse could not be ported: it shares `widgets.png` with the hotbar highlight
   and runs at 100 times its frame rate.
4. **`tabs.png` is stretched from 26 to 28 px per column** for 1.19.3+, where the column width
   changed and an extra tab was added. The geometry lines up; the rounded corners are slightly
   flattened.
5. **Cells that had to fall back to vanilla** expose vanilla-coloured patches. Exact coordinates are
   listed in `work/build-report.json` under `art_todo`.
6. **The bundled font does not work with "Force Unicode"**, because the upstream pack replaces the
   whole `font/uniform.json` with bitmap emoji and UI glyphs. This is upstream behaviour; build with
   `--no-fonts` to avoid it.
7. **Third-party mod textures are not version-checked** (18 namespaces). They apply only when the mod
   version matches, and are removed entirely from the 1.6.1 – 1.12.2 files.

## License

CozyUI+ is licensed **GPL-3.0-only**, and its fonts are Noto Sans (SIL OFL 1.1) and Fluent Emoji
(MIT). This port is a modified redistribution of that art under the same license. Full attribution
and a per-item list of modifications are in [`NOTICE`](NOTICE); the license text is in
[`LICENSE`](LICENSE), with both font licenses alongside it.

* Art, design, fonts, original pack — **零雾〇五 Fogg05**
* Low-version port, packaging, tooling — **CollinsLiu**
