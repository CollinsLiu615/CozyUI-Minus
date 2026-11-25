# CozyUI-

### A neat, subtle, high-definition interface for Minecraft — now from **1.6.1** to **1.19.4**

CozyUI- restyles the entire user interface into a clean, soft, high-definition look. Every
vanilla screen is covered, plus a long list of client mods.

This is the **low-version port of [CozyUI+](https://modrinth.com/resourcepack/cozyui-plus)** by
**零雾〇五 (Fogg05)**. The art, the fonts, the tooltip tricks and the mod skins are the original
author's work. Nothing was redesigned — the same files are re-packaged and re-aligned so the
pack also loads on the versions the original never targeted.

---

## In memory

Fogg05, the creator of CozyUI+, has passed away.

Everything in this pack was made by them: every panel, every rounded corner, the colour choices,
the bundled fonts. This port deliberately adds **no new art** — it only carries their work down
to older versions, so that players still on 1.6, 1.12 or 1.16 can use the interface they made.
If you enjoy it, the credit belongs to them. Please keep that in mind when you share it.

> 原作者 零雾〇五 Fogg05 已离世。这个包里的每一块界面都出自他手；本移植只做版本适配，
> 不另作美术，只是把他的作品带到更老的版本里。谢谢他留下的东西。

---

## What it does

* **Complete vanilla UI restyle** — inventory, chests, workbenches, furnaces, anvils, enchanting,
  brewing, villager trading, the creative inventory, the HUD, menus and the title screen.
  *(On 1.6.1 – 1.12.2 a few controls stay vanilla — see the table further down.)*
* **Emoji+ & MCsans+ bundled** *(1.13 and newer)* — the font is replaced with high-definition
  **Noto Sans**, and emoji with Microsoft's **Fluent Emoji**. Below 1.13 Minecraft has no JSON
  font system, so those versions keep the vanilla font.
* **Brewing stand recipes drawn on the interface** *(1.13 and newer — they ride on the bundled font)*
  — all recipes are painted onto the brewing stand GUI so you don't have to remember them.
* **Small icons in front of enchantment names** *(1.13 and newer)* — enchanted books list their
  enchantments with a little icon in front of each name.
* **OptiGUI support** *(1.19 and newer, with the mod installed)* — colored shulker boxes, droppers,
  dispensers and ender chests become distinguishable by their background colour.
* **RGB-cycling experience bar and item highlight** — a very slow, deliberately soothing
  **40-second** hue cycle, reimplemented as an 8-frame sheet animation (the original uses the
  native sprite format that only exists on 1.20.2+). *(Both the bar and the hotbar highlight on
  1.13 and newer; on 1.6.1 – 1.12.2 the experience bar cycles but the highlight stays vanilla,
  because those versions keep the vanilla `widgets.png`.)*
* **Animated UI buttons** — **not included in this port.** The original draws it as a 16-frame
  pulse on `widgets.png`, the same sheet that carries the item highlight, and one sheet cannot hold
  two animation definitions. (The original only supports it on 1.21+ anyway.)

## Mods covered

| Mod | | Mod | |
|---|:--:|---|:--:|
| OptiGUI | ⭐ recommended | AppleSkin | optional |
| Detail Armor Bar | optional | Litematica | optional |
| MiniHUD | optional | ReplayMod | optional |
| Inventory HUD+ | optional | Dynamic Crosshair | optional |
| Jade | optional | REI | optional |
| JEI | optional | Inventory Profiles Next | optional |
| Xaero's Minimap | optional | Xaero's World Map | optional |
| Mod Menu | optional | No Chat Reports | optional |
| Simple Voice Chat | optional | Entity Features | optional |
| Overflowing Bars | optional | | |

Mod skins follow each mod's own version — they only appear when that mod version actually uses
the same texture layout. *(1.13 and newer; the 1.6.1 – 1.12.2 files ship no mod textures at all.)*

Start with **OptiGUI** if you install only one: it is what enables the colored container
backgrounds. It needs 1.19 or newer.

---

## Supported versions

Pick the file that matches your game version. Every file is a self-contained resource pack, and
**each one declares the exact pack format of the versions it covers — so Minecraft never shows a
"made for a different version" notice.**

| File | Minecraft | Pack format |
|---|---|:--:|
| `CozyUI-_1.6.1-1.8.9.zip` | **1.6.1 – 1.8.9** | 1 |
| `CozyUI-_1.9-1.10.2.zip` | 1.9 – 1.10.2 | 2 |
| `CozyUI-_1.11-1.12.2.zip` | 1.11 – 1.12.2 | 3 |
| `CozyUI-_1.13-1.14.4.zip` | 1.13 – 1.14.4 | 4 |
| `CozyUI-_1.15-1.16.1.zip` | 1.15 – 1.16.1 | 5 |
| `CozyUI-_1.16.2-1.16.5.zip` | 1.16.2 – 1.16.5 | 6 |
| `CozyUI-_1.17-1.17.1.zip` | 1.17 – 1.17.1 | 7 |
| `CozyUI-_1.18-1.18.2.zip` | 1.18 – 1.18.2 | 8 |
| `CozyUI-_1.19-1.19.2.zip` | 1.19 – 1.19.2 | 9 |
| `CozyUI-_1.19.3.zip` | 1.19.3 | 12 |
| `CozyUI-_1.19.4.zip` | 1.19.4 | 13 |

That is **63 release versions**, one file per pack-format generation, and **zero format warnings**.

For **1.20 and newer**, use the original **[CozyUI+](https://modrinth.com/resourcepack/cozyui-plus)**
release — it covers 1.20 through 1.21.11.

Pack format 1 spans 1.6.1 – 1.8.9, so the oldest file reaches back to 1.6 and 1.7. 1.6.1 is also
where Minecraft introduced the current `assets/` resource-pack layout — 1.5.2 and older used the
old texture-pack format, which cannot carry this pack at all.

Measured on 1.6.1 and 1.6.4 against 1.8.9: exactly **one**
of the 26 shipped GUI sheets (the enchanting table, 1.5 % of its pixels); `widgets.png` and
`icons.png` are pixel-identical, and the gradient regions sit at the same coordinates.

## What works on which version

Being honest about the old end — the UI was reshaped several times before 1.20, and where the
layout of a sheet changed too much, the port leaves that sheet vanilla rather than shipping
something misaligned:

| | 1.13+ | 1.6.1 – 1.12.2 |
|---|:--:|:--:|
| Container panels (inventory, chest, furnace, crafting, brewing, beacon, hopper, anvil, enchanting, villager…) | ✅ | ✅ |
| Title-screen panorama | ✅ | ✅ |
| Buttons, sliders, text fields, hotbar (`widgets.png`) | ✅ | ❌ vanilla |
| HUD hearts / food / armour (`icons.png`) | ✅ | ✅ |
| Creative tab plates | ✅ | ✅ |
| Bundled font (Emoji+ / MCsans+) | ✅ | ❌ not applicable |
| Brewing recipes & enchantment icons | ✅ | ❌ they ride on the bundled font |
| Mod skins | ✅ | ❌ |
| Colored containers via OptiGUI | ✅ with the mod | ❌ not applicable |
| RGB-cycling XP bar | ✅ 40-second loop | ✅ 40-second loop |
| RGB-cycling hotbar highlight | ✅ 40-second loop | ❌ `widgets.png` stays vanilla |

On 1.6.1 – 1.12.2 the pack is small (about 5 MB) because it only ships the sheets that actually
exist in those versions — no dead weight.

## Installation

1. Download the file for your version.
2. Drop it into `.minecraft/resourcepacks/` (do **not** unzip it).
3. In game: *Options → Resource Packs*, enable **CozyUI-**.
4. Optional: install **OptiGUI** (1.19+) for the coloured container backgrounds.

## Notes

* **This is a resource pack, not a mod.** No loader, no Java, no dependencies.
* Load order: keep CozyUI- **above** other UI packs and **below** anything you want to override it.
* On 1.6 – 1.12 the resource-pack screen looks different, but the folder and the steps are the same.
* You should **never** see a "made for a different version" notice — every file declares the exact
  pack format of the range printed in its name. If you do see one, you picked the wrong file.

## Credits & license

* **Art, design, fonts, original pack** — 零雾〇五 **Fogg05** (original CozyUI+ author)
* **Low-version port, packaging, tooling** — **CollinsLiu**
* **Fonts** — [Noto Sans](https://github.com/notofonts/noto-cjk) (SIL OFL) and
  [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) (MIT)
* Emoji+ / MCsans+ by Fogg05

Original project: <https://modrinth.com/resourcepack/cozyui-plus> ·
<https://github.com/Fogg05/CozyUI-Plus>

Licensed **GPL-3.0**, same as the original. You may redistribute and modify it, but it must stay
open source and the credits above must remain.
