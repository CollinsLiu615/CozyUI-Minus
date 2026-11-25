#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CozyUI+ 单包通吃构建器 / universal pack builder
===============================================

上游的做法是「一个 zip 声明支持 1.20 ~ 1.21.11」：老版式大图和新版式 sprite
**同时**放进包里，游戏只读自己认识的那套，多余的被忽略。降到 1.20 以下还能不能
继续用一个包？先把「跨版本同路径冲突」讲清楚：

* 1.20.2 起 GUI 大图拆成 sprite，但 `gui/container/*.png` 这类**容器底板仍是平铺大图**。
  它们生成代际变化的是「槽位凹陷从底板里移除、改由 sprite 叠画」——上游留的是带凹陷的
  1.20.1 版：在 1.20.2+ 上凹陷会被 sprite 盖住，不会重复；反过来留无凹陷版则 1.20.1
  会出现空洞。所以**上游的单美术选择本身就是兼容的**，我们沿用。
* 真正互斥（同一路径、两个版本组都要不同版式、无法兼顾）的只有 `tabs.png` 一张：
    - ≤1.19.2 : 7 列 × 28px
    - 1.19.3 ~ 1.20.1 : 8 列 × 26px
    - 1.20.2+ : **不再读它**（改用 `gui/sprites/container/creative_inventory/tab_*.png`）
  也就是说这个冲突的影响面只到 1.20.1，**碰不到 1.20.2+**。
  另外页签「图标」来自独立的 `tab_items.png` / `tab_inventory.png` / `tab_item_search.png`，
  对不齐的只是底板接缝与圆角，不会出现"图标跑到别的页上"。

于是提供两种通吃包：

  all-versions             沿用上游 8×26 美术（1.19.3+ 完美；≤1.19.2 底板有接缝错位）
  all-versions-legacy-tabs 把 26px 列拉伸成 28px（≤1.19.2 完美；1.19.3~1.20.1 有接缝错位）

`pack_format` 取整个区间的最低值 6：这样 1.16.2~1.16.5 零提示，1.17+ 会显示
"为旧版本制作"的黄色提示（仍可正常启用），1.20.2+ 走 `supported_formats` 无提示。
单个整数天生无法让所有版本都不提示——这是"一个包通吃"本身的代价，不是本次移植引入的。

用法：
    python3 tools/build_universal.py            # 两个都出
    python3 tools/build_universal.py --only all-versions
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402  复用版式规则与图集工具

ROOT = B.ROOT
DIST_DIR = B.DIST_DIR
MIN_FMT = 6          # 1.16.2 ~ 1.16.5
MAX_FMT = 9999       # 与上游一致：对 1.20.2+ 声明"整个区间都支持"
MC_RANGE = "1.16.2 - 1.21.11"

TABS = "assets/minecraft/textures/gui/container/creative_inventory/tabs.png"

VARIANTS = {
    "all-versions": dict(tabs="modern",
                         note="upstream 8x26 tab art"),
    "all-versions-legacy-tabs": dict(tabs="legacy",
                                     note="26px columns stretched to 28px for <=1.19.2"),
}


def mcmeta() -> bytes:
    desc = (f"§cCozyUI§b- §7v1.10 §8[§7MC {MC_RANGE}§8]§r\n"
            f"§7by §f零雾〇五 Fogg05 §7· §flow-version port: §fCollinsLiu")
    doc = {"pack": {
        "pack_format": MIN_FMT,          # 老版本只认这个字段 → 取区间最低值
        "supported_formats": [MIN_FMT, MAX_FMT],  # 1.20.2+
        "min_format": MIN_FMT,           # 1.21.9+
        "max_format": MAX_FMT,
        "description": desc,
    }}
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build(name: str, src: zipfile.ZipFile) -> dict:
    cfg = VARIANTS[name]
    out_path = os.path.join(DIST_DIR, f"CozyUI-_{name}.zip")
    tabs_changed = False

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        zout.writestr("pack.mcmeta", mcmeta())
        if os.path.exists(B.PACK_ICON):
            with open(B.PACK_ICON, "rb") as fh:
                zout.writestr("pack.png", fh.read())
        for entry in src.namelist():
            if entry.endswith("/") or entry in ("pack.mcmeta", "pack.png"):
                continue
            data = src.read(entry)
            if entry == TABS and cfg["tabs"] == "legacy":
                pack_img = Image.open(io.BytesIO(data)).convert("RGBA")
                v_src = B.vanilla_png(B.BASELINE, entry)
                v_tgt = B.vanilla_png("1.19.2", entry)
                fixed, note = B.build_texture(entry, pack_img, v_src, v_tgt)
                if note["action"] == "columns":
                    data = B.to_png(fixed)
                    tabs_changed = True
                    coverage = note.get("columns_coverage")
                else:  # 兜底：规则没命中就保持原样，不要静默改图
                    coverage = None
            zout.writestr(entry, data)

    return {
        "variant": name,
        "zip": os.path.relpath(out_path, ROOT),
        "bytes": os.path.getsize(out_path),
        "pack_format": MIN_FMT,
        "supported_formats": [MIN_FMT, MAX_FMT],
        "mc_range": MC_RANGE,
        "tabs": cfg["tabs"],
        "tabs_remapped": tabs_changed,
        "note": cfg["note"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(VARIANTS))
    args = ap.parse_args()

    os.makedirs(DIST_DIR, exist_ok=True)
    src = zipfile.ZipFile(B.SRC_PACK)
    names = [args.only] if args.only else list(VARIANTS)
    reps = []
    for n in names:
        r = build(n, src)
        print(f'>>> {n:26s} {r["bytes"]/1e6:6.1f}MB '
              f'fmt={r["pack_format"]}+supported={r["supported_formats"]} '
              f'tabs={r["tabs"]}{" (remapped)" if r["tabs_remapped"] else ""}')
        reps.append(r)

    out = os.path.join(B.WORK_DIR, "universal-report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(reps, fh, ensure_ascii=False, indent=2)
    print(f"\nreport -> {os.path.relpath(out, ROOT)}")
    return 0 if all(r["tabs"] == "modern" or r["tabs_remapped"] for r in reps) else 1


if __name__ == "__main__":
    sys.exit(main())
